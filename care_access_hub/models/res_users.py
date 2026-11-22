# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    # مسمّيات متعددة للمستخدم الواحد — الصلاحية الفعلية = اتحاد (الأعلى)
    care_role_ids = fields.Many2many(
        'care.job.role', 'care_user_role_rel', 'user_id', 'role_id',
        string='المسمّيات الوظيفية')
    care_role_label = fields.Char(string='المسمّيات', compute='_compute_role_label')
    # عدّاد مجموعات أودو الحالية — لإظهار فوضى الإسناد العشوائي (110 متوسّط)
    care_group_count = fields.Integer(string='عدد المجموعات الحالية', compute='_compute_group_count')

    @api.depends('care_role_ids')
    def _compute_role_label(self):
        for u in self:
            u.care_role_label = ' + '.join(u.care_role_ids.mapped('name')) or ''

    @api.depends('groups_id')
    def _compute_group_count(self):
        for u in self:
            u.care_group_count = len(u.groups_id)

    # محلّل الفرق (diff): المبرّر بالمسمّيات مقابل الزائد العشوائي — dry-run آمن
    care_role_group_ids = fields.Many2many(
        'res.groups', string='مجموعات المسمّيات', compute='_compute_diff')
    care_excess_count = fields.Integer(string='مجموعات زائدة (غير مبرّرة)', compute='_compute_diff')
    care_missing_count = fields.Integer(string='مجموعات ناقصة (يحتاجها المسمّى)', compute='_compute_diff')

    @api.depends('care_role_ids', 'care_role_ids.odoo_group_ids', 'groups_id')
    def _compute_diff(self):
        ess = self.env.ref('base.group_user', raise_if_not_found=False)
        for u in self:
            rg = u.care_role_ids.mapped('odoo_group_ids')
            u.care_role_group_ids = rg
            excess = u.groups_id - rg
            if ess:
                excess = excess - ess
            u.care_excess_count = len(excess)
            u.care_missing_count = len(rg - u.groups_id)

    def action_access_diff(self):
        """معاينة الفرق: المبرّر / الزائد / الناقص — بلا أي تعديل."""
        self.ensure_one()
        msg = _(
            'المسمّيات: %(r)s\nمجموعات حالية: %(cur)s\nمبرّرة بالمسمّيات: %(j)s\n'
            '⚠️ زائدة (مرشّحة للتجريد): %(x)s\nناقصة (يحتاجها المسمّى): %(m)s'
        ) % {
            'r': self.care_role_label or '—', 'cur': len(self.groups_id),
            'j': len(self.care_role_group_ids), 'x': self.care_excess_count,
            'm': self.care_missing_count,
        }
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('تحليل صلاحيات %s') % self.name,
                           'message': msg, 'sticky': True, 'type': 'warning'}}

    def action_apply_roles(self):
        """تطبيق آمن (إضافة فقط): يمنح المستخدم مجموعات مسمّياته دون حذف شيء.
        التجريد الكامل للعشوائية مرحلة ترحيل لاحقة مُبوّبة ومُختبَرة."""
        for u in self:
            grps = u.care_role_ids.mapped('odoo_group_ids')
            if grps:
                u.sudo().write({'groups_id': [(4, g.id) for g in grps]})
        return True

    def action_preview_effective(self):
        """معاينة الصلاحية الفعلية (اتحاد المسمّيات) — dry-run لا يعدّل شيئًا."""
        self.ensure_one()
        roles = self.care_role_ids
        scope = 'كل الشركة' if any(r.data_scope == 'all' for r in roles) else 'مشاريعه فقط'
        groups = roles.mapped('odoo_group_ids')
        msg = _('المسمّيات: %(roles)s\nنطاق البيانات: %(scope)s\nمجموعات أودو المقترحة: %(n)s') % {
            'roles': self.care_role_label or '—', 'scope': scope, 'n': len(groups)}
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('المعاينة الفعلية'), 'message': msg, 'sticky': True, 'type': 'info'},
        }
