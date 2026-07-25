# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


USER_TYPE_GROUP = {
    'portal': 'base.group_portal',
    'internal': 'base.group_user',
    'public': 'base.group_public',
}


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Show ALL users (portal / public / internal) in the "Related User" picker,
    # not just internal — so an employee can be linked to any account type.
    user_id = fields.Many2one(domain=[])

    # --- create a new account of a chosen type ---
    app_user_type = fields.Selection([
        ('portal', 'بورتال (Portal)'),
        ('internal', 'داخلي كامل (Internal)'),
        ('public', 'عام (Public)'),
    ], string='نوع الحساب', default='portal',
        help='Portal: محدود ويعمل مع التطبيق · Internal: كامل الصلاحيات · '
             'Public: لا يستطيع الدخول للتطبيق (تحذير).')
    app_user_pms = fields.Boolean(string='مستخدم إدارة المشاريع', default=True,
                                  help='يمنح الحساب صلاحية تطبيق إدارة المشاريع.')
    # --- or link an existing account (any type) ---
    link_user_id = fields.Many2one('res.users', string='ربط حساب موجود', copy=False)
    linked_user_share = fields.Boolean(related='user_id.share', string='حساب خارجي')

    def _employee_login(self):
        self.ensure_one()
        login = (self.work_email or getattr(self, 'private_email', False)
                 or (self.barcode and '%s@care-kw.com' % self.barcode)
                 or (self.mobile_phone or self.work_phone))
        if not login:
            raise UserError(_('لا يوجد بريد/بادج/هاتف لإنشاء اسم دخول. أضف بريد العمل أولًا.'))
        return login.strip()

    def _attach_user(self, user):
        """Link the user to this employee both ways + set the PMS flag."""
        self.ensure_one()
        self.sudo().write({'user_id': user.id})
        if self.app_user_pms and 'pms_app_user' in user._fields:
            user.sudo().write({'pms_app_user': True})

    def action_create_app_user(self):
        self.ensure_one()
        if self.user_id:
            raise UserError(_('هذا العامل مرتبط بمستخدم بالفعل: %s') % self.user_id.login)
        login = self._employee_login()
        Users = self.env['res.users'].sudo()
        if Users.with_context(active_test=False).search_count([('login', '=', login)]):
            raise UserError(_('يوجد مستخدم بنفس اسم الدخول (%s) — استخدم «ربط حساب موجود».') % login)
        group = self.env.ref(USER_TYPE_GROUP[self.app_user_type or 'portal'])
        vals = {
            'name': self.name, 'login': login,
            'email': self.work_email or False,
            'groups_id': [(6, 0, [group.id])],
        }
        if self.app_user_pms and 'pms_app_user' in Users._fields:
            vals['pms_app_user'] = True
        user = Users.with_context(no_reset_password=True, mail_create_nosubscribe=True).create(vals)
        self._attach_user(user)
        self.message_post(body=_('تم إنشاء حساب %s (%s) وربطه بالعامل.')
                          % (login, dict(self._fields['app_user_type'].selection).get(self.app_user_type)))
        return {
            'type': 'ir.actions.act_window', 'res_model': 'res.users',
            'res_id': user.id, 'view_mode': 'form', 'target': 'current',
        }

    def action_link_existing_user(self):
        self.ensure_one()
        if not self.link_user_id:
            raise UserError(_('اختر حسابًا موجودًا للربط.'))
        if self.user_id and self.user_id.id != self.link_user_id.id:
            raise UserError(_('هذا العامل مرتبط بمستخدم آخر بالفعل: %s') % self.user_id.login)
        other = self.sudo().search([('user_id', '=', self.link_user_id.id), ('id', '!=', self.id)], limit=1)
        if other:
            raise UserError(_('هذا الحساب مرتبط بعامل آخر: %s') % other.name)
        self._attach_user(self.link_user_id)
        self.message_post(body=_('تم ربط الحساب %s بالعامل.') % self.link_user_id.login)

    def action_unlink_app_user(self):
        self.ensure_one()
        self.sudo().write({'user_id': False})
