# -*- coding: utf-8 -*-
"""Operation roles on a collection order — operations manager, driver and the
final-quantity receiver — each notified (in-app push + chatter + activity) when
assigned, so the right person gets the job on their phone."""
from odoo import api, fields, models, _


class ServiceOrderRoles(models.Model):
    _inherit = 'service.order'

    ops_manager_id = fields.Many2one('res.users', string='مسؤول العمليات', tracking=True)
    driver_id = fields.Many2one('res.users', string='السائق', tracking=True)
    receiver_id = fields.Many2one('res.users', string='مستلم الكميات النهائية', tracking=True)
    proof_image = fields.Image(string='صورة إثبات', max_width=1920, max_height=1920)
    final_weight = fields.Float(string='الوزن النهائي المستلم')
    final_note = fields.Char(string='ملاحظة المستلم')

    def _notify_role(self, user, role_label):
        if not user:
            return
        self.ensure_one()
        title = _('طلب نقل %s') % (self.serial or '')
        body = _('أُسند إليك دور «%s» في الطلب %s') % (role_label, self.serial or '')
        if 'care.cafm.notification' in self.env:
            try:
                self.env['care.cafm.notification'].sudo().push(user, title, body, ntype='task', author=self.env.user)
            except Exception:
                pass
        try:
            self.activity_schedule('mail.mail_activity_data_todo', user_id=user.id, summary=body)
        except Exception:
            pass
        self.message_post(body=_('👤 %s: %s') % (role_label, user.name),
                          partner_ids=user.partner_id.ids)

    # friendly, client-facing message per collection-order state
    _CLIENT_STATE_MSG = {
        'scheduled': ('📅 تم جدولة طلبكم', 'تم جدولة طلب نقل النفايات %s وسيتم الالتقاط قريبًا.'),
        'pickuped': ('🚛 تم الالتقاط', 'تم التقاط المخلفات من موقعكم للطلب %s.'),
        'arrived': ('🏭 وصلت الشحنة', 'وصلت شحنة الطلب %s إلى مركز المعالجة.'),
        'processing': ('♻️ جارٍ المعالجة', 'جارٍ معالجة مخلفات الطلب %s بطريقة صحيحة.'),
        'delivered': ('✅ تم التسليم', 'تم استلام ومعالجة مخلفات الطلب %s.'),
        'completed': ('🎉 اكتمل الطلب', 'اكتمل طلب نقل ومعالجة النفايات %s. شكرًا لكم.'),
        'cancelled': ('✖ تم إلغاء الطلب', 'تم إلغاء طلب النفايات %s.'),
    }

    def _client_users(self):
        """Portal users of the client that owns this order (via project.contact_id
        and any care.cafm.client membership)."""
        self.ensure_one()
        partner = self.project_id.contact_id if 'contact_id' in self.project_id._fields else False
        users = self.env['res.users'].sudo()
        if partner:
            users |= self.env['res.users'].sudo().search([('partner_id', '=', partner.id)])
            if 'care.cafm.client' in self.env:
                clients = self.env['care.cafm.client'].sudo().search([('partner_id', '=', partner.id)])
                users |= clients.mapped('user_ids')
        return users

    def _notify_client_state(self, state):
        self.ensure_one()
        msg = self._CLIENT_STATE_MSG.get(state)
        if not msg or 'care.cafm.notification' not in self.env:
            return
        users = self._client_users()
        if not users:
            return
        title, body_tpl = msg
        try:
            self.env['care.cafm.notification'].sudo().push(
                users, title, body_tpl % (self.serial or ''), ntype='info',
                action_url='/service_order/%s' % self.id)
        except Exception:
            pass

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        for r in recs:
            r._notify_role(r.ops_manager_id, _('مسؤول العمليات'))
            r._notify_role(r.driver_id, _('السائق'))
            r._notify_role(r.receiver_id, _('مستلم الكميات'))
        return recs

    def write(self, vals):
        res = super().write(vals)
        for r in self:
            if vals.get('ops_manager_id'):
                r._notify_role(r.ops_manager_id, _('مسؤول العمليات'))
            if vals.get('driver_id'):
                r._notify_role(r.driver_id, _('السائق'))
            if vals.get('receiver_id'):
                r._notify_role(r.receiver_id, _('مستلم الكميات'))
            # notify the CLIENT on every status change of their order
            if vals.get('states'):
                r._notify_client_state(vals['states'])
        return res
