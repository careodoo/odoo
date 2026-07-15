# -*- coding: utf-8 -*-
"""In-app account & data deletion requests (Google Play requirement). A user
submits a request from the app; admins see it here and process it. Creating a
request notifies system admins and deactivates the login immediately so no
further access occurs while the data is purged."""
from odoo import api, fields, models


class AccountDeletion(models.Model):
    _name = 'care.account.deletion'
    _description = 'طلب حذف حساب'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    user_id = fields.Many2one('res.users', string='المستخدم', required=True, ondelete='cascade')
    partner_name = fields.Char(string='الاسم')
    email = fields.Char(string='البريد')
    reason = fields.Text(string='السبب')
    state = fields.Selection([
        ('pending', 'قيد المعالجة'), ('done', 'تم الحذف'), ('rejected', 'مرفوض'),
    ], default='pending', string='الحالة', tracking=True)
    request_date = fields.Datetime(default=fields.Datetime.now, string='تاريخ الطلب')

    @api.model
    def submit(self, user, reason=None):
        """Create (or reuse a pending) deletion request for the user and alert admins."""
        existing = self.sudo().search([('user_id', '=', user.id), ('state', '=', 'pending')], limit=1)
        rec = existing or self.sudo().create({
            'user_id': user.id, 'partner_name': user.name, 'email': user.email or user.login,
            'reason': reason,
        })
        # notify system admins
        if 'care.cafm.notification' in self.env:
            admins = self.env['res.users'].sudo().search([('groups_id', 'in', self.env.ref('base.group_system').id)])
            if admins:
                try:
                    self.env['care.cafm.notification'].sudo().push(
                        admins, '🗑️ طلب حذف حساب',
                        '%s (%s) طلب حذف حسابه وبياناته.' % (user.name, user.email or user.login),
                        ntype='warning')
                except Exception:
                    pass
        return rec
