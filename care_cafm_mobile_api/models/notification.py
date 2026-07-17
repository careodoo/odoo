# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CafmNotification(models.Model):
    """One row per recipient — so read-state is per user and querying the mobile
    inbox is trivial. Broadcasts are expanded into many rows on send."""
    _name = 'care.cafm.notification'
    _description = 'CAFM Notification'
    _order = 'create_date desc'

    title = fields.Char(string='العنوان', required=True)
    body = fields.Text(string='النص')
    ntype = fields.Selection([
        ('info', 'معلومة'), ('task', 'مهمة'), ('warning', 'تنبيه'), ('alert', 'طوارئ'),
    ], string='النوع', default='info', required=True)
    user_id = fields.Many2one('res.users', string='المستلم', required=True, ondelete='cascade', index=True)
    author_id = fields.Many2one('res.users', string='المُرسِل', default=lambda s: s.env.user)
    is_read = fields.Boolean(string='مقروء', default=False)
    read_date = fields.Datetime(string='تاريخ القراءة')
    action_url = fields.Char(string='رابط/إجراء', help='مسار داخل التطبيق يُفتح عند النقر (اختياري).')
    batch = fields.Char(string='دفعة الإرسال', index=True,
                        help='معرّف مشترك لكل رسائل نفس البثّ — لعرض المستقبِلين ومَن قرأ.')

    def mark_read(self):
        self.filtered(lambda n: not n.is_read).write({
            'is_read': True, 'read_date': fields.Datetime.now()})

    @api.model
    def push(self, users, title, body=None, ntype='info', author=None, action_url=None, batch=None):
        """Create a notification row for each user. Returns the created records."""
        vals = [{
            'title': title, 'body': body, 'ntype': ntype, 'user_id': u.id,
            'author_id': (author or self.env.user).id, 'action_url': action_url, 'batch': batch,
        } for u in users]
        recs = self.sudo().create(vals)
        # fan out an OS-level device push (best-effort; no-op if FCM unset)
        try:
            if 'care.cafm.device' in self.env:
                self.env['care.cafm.device'].send_to_users(
                    users, title, body, data={'action_url': action_url or '', 'ntype': ntype})
        except Exception:
            pass
        return recs


class CafmScheduledNotification(models.Model):
    """A notification whose delivery is deferred to a future time. Recipients are
    snapshotted at scheduling time (deterministic), and a cron dispatches any that
    have come due."""
    _name = 'care.cafm.notification.scheduled'
    _description = 'إشعار مجدول'
    _order = 'scheduled_datetime asc'

    title = fields.Char(string='العنوان', required=True)
    body = fields.Text(string='النص')
    ntype = fields.Selection([
        ('info', 'معلومة'), ('task', 'مهمة'), ('warning', 'تنبيه'), ('alert', 'طوارئ'),
    ], string='النوع', default='info', required=True)
    audience_label = fields.Char(string='الجمهور')
    user_ids = fields.Many2many('res.users', string='المستلمون')
    scheduled_datetime = fields.Datetime(string='موعد الإرسال', required=True, index=True)
    author_id = fields.Many2one('res.users', string='المُرسِل', default=lambda s: s.env.user)
    batch = fields.Char(string='دفعة الإرسال', index=True)
    state = fields.Selection([
        ('pending', 'بانتظار الإرسال'), ('sent', 'أُرسل'), ('cancelled', 'ملغى'),
    ], string='الحالة', default='pending', index=True)
    recipients_count = fields.Integer(string='عدد المستلمين', compute='_compute_rc', store=True)

    @api.depends('user_ids')
    def _compute_rc(self):
        for r in self:
            r.recipients_count = len(r.user_ids)

    def action_cancel(self):
        self.filtered(lambda r: r.state == 'pending').write({'state': 'cancelled'})

    def _dispatch(self):
        for r in self:
            recips = r.user_ids.filtered('active')
            if recips:
                self.env['care.cafm.notification'].sudo().push(
                    recips, r.title, r.body, ntype=r.ntype, author=r.author_id, batch=r.batch)
            r.state = 'sent'

    @api.model
    def _cron_dispatch(self):
        due = self.sudo().search([
            ('state', '=', 'pending'), ('scheduled_datetime', '<=', fields.Datetime.now())])
        due._dispatch()


class CafmNotificationCompose(models.TransientModel):
    """Backend panel to compose and send a notification to any audience."""
    _name = 'care.cafm.notification.compose'
    _description = 'إرسال إشعار'

    title = fields.Char(string='العنوان', required=True)
    body = fields.Text(string='النص')
    ntype = fields.Selection([
        ('info', 'معلومة'), ('task', 'مهمة'), ('warning', 'تنبيه'), ('alert', 'طوارئ'),
    ], string='النوع', default='info', required=True)
    audience = fields.Selection([
        ('user', 'مستخدم محدّد'),
        ('users', 'عدة مستخدمين'),
        ('internal', 'كل الموظفين (داخلي)'),
        ('portal', 'كل العملاء (بوابة)'),
        ('all', 'الجميع'),
        ('service', 'فريق خدمة'),
    ], string='الجمهور', default='user', required=True)
    user_id = fields.Many2one('res.users', string='المستخدم')
    user_ids = fields.Many2many('res.users', string='المستخدمون')
    service_id = fields.Many2one('care.cafm.service', string='الخدمة')

    def _recipients(self):
        U = self.env['res.users']
        if self.audience == 'user':
            return self.user_id
        if self.audience == 'users':
            return self.user_ids
        if self.audience == 'internal':
            return U.search([('share', '=', False), ('active', '=', True)])
        if self.audience == 'portal':
            return U.search([('share', '=', True), ('active', '=', True)])
        if self.audience == 'all':
            return U.search([('active', '=', True)])
        if self.audience == 'service' and self.service_id:
            wos = self.env['care.cafm.workorder'].search([('service_type', '=', self.service_id.service_type)])
            emps = wos.mapped('employee_id')
            return emps.mapped('user_id')
        return U.browse()

    def action_send(self):
        self.ensure_one()
        recips = self._recipients()
        if not recips:
            raise UserError(_('لا مستلمين مطابقين لهذا الاختيار.'))
        self.env['care.cafm.notification'].push(
            recips, self.title, self.body, self.ntype, author=self.env.user)
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('تم الإرسال'),
                       'message': _('أُرسِل الإشعار إلى %d مستخدم.') % len(recips),
                       'type': 'success', 'sticky': False,
                       'next': {'type': 'ir.actions.act_window_close'}},
        }
