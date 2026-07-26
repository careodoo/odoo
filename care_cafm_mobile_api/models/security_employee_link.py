# -*- coding: utf-8 -*-
"""ربط تلقائي بين عضو فريق الأمن (security.employee) وحساب دخول (res.users)، حتى
يفتح الحارس واجهة الأمن في التطبيق مباشرةً دون ربط يدوي. عند إضافة العضو لفريق
يُنشأ/يُربط له حساب بورتال (باسم دخول من البريد أو كود الموظف/الرقم المدني)."""
import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class SecurityEmployee(models.Model):
    _inherit = 'security.employee'

    def _cc_emails(self):
        self.ensure_one()
        for v in (self.work_email, self.email, self.private_email,
                  self.employee_id.work_email if self.employee_id else False):
            if v and '@' in v:
                return v.strip().lower()
        return False

    def _provision_login(self, create=True):
        """يربط بمستخدم قائم بالبريد، أو يُنشئ حساب بورتال جديداً. يرجع المستخدم."""
        self.ensure_one()
        if self.user_id:
            return self.user_id
        Users = self.env['res.users'].sudo().with_context(active_test=False)
        email = self._cc_emails()
        # 1) ربط بمستخدم قائم بنفس البريد
        if email:
            ex = Users.search(['|', ('login', '=', email), ('email', '=', email)], limit=1)
            if ex:
                self.user_id = ex.id
                return ex
        if not create:
            return False
        # 2) إنشاء حساب بورتال جديد — اسم دخول من البريد أو الكود/الرقم المدني
        login = email or (self.employee_code or self.civil_code or ('guard-%s' % self.id))
        login = str(login).strip().replace(' ', '')
        if Users.search_count([('login', '=', login)]):
            login = '%s-%s' % (login, self.id)
        # كلمة مرور أوّلية معروفة للعامل (الرقم المدني/الكود) — يغيّرها لاحقاً
        pw = str(self.civil_code or self.employee_code or ('Care@%s' % self.id))
        try:
            user = self.env['res.users'].sudo().with_context(
                no_reset_password=True, mail_create_nosubscribe=True).create({
                'name': self.name or self.display_name or login,
                'login': login,
                'email': email or False,
                'password': pw,
                'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
            })
            self.user_id = user.id
            return user
        except Exception as e:
            _logger.warning('تعذّر إنشاء حساب لعضو الأمن %s: %s', self.display_name, e)
            return False

    def action_provision_login(self):
        """زر/إجراء: وفّر حساب دخول لكل عضو محدّد (للربط اليدوي أو الجماعي)."""
        for rec in self:
            rec._provision_login(create=True)
        return True

    def _autolink_enabled(self):
        # يمكن الإيقاف عبر باراميتر النظام care.security.autouser=0
        return self.env['ir.config_parameter'].sudo().get_param('care.security.autouser', '1') != '0'

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        if self._autolink_enabled():
            for rec in recs:
                if not rec.user_id and rec.team_ids:
                    try:
                        rec._provision_login(create=True)
                    except Exception as e:
                        _logger.warning('autolink (create) فشل لـ %s: %s', rec.display_name, e)
        return recs

    def write(self, vals):
        res = super().write(vals)
        # عند إضافته لفريق ولمّا يُربط بعد → وفّر له حساباً
        if self._autolink_enabled() and 'team_ids' in vals:
            for rec in self:
                if not rec.user_id and rec.team_ids:
                    try:
                        rec._provision_login(create=True)
                    except Exception as e:
                        _logger.warning('autolink (write) فشل لـ %s: %s', rec.display_name, e)
        return res
