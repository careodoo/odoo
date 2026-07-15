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
        return res
