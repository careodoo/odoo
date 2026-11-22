# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

# ترتيب الطبقات الهرمية للمسمّيات الوظيفية
TIERS = [
    ('exec', 'القيادة التنفيذية'),
    ('manager', 'مدراء الإدارات'),
    ('deputy', 'المساعدون والكبار'),
    ('officer', 'المسؤولون والموظفون'),
    ('field', 'الميدان (منطَّق بالمشاريع)'),
]


class CareJobRole(models.Model):
    """المسمّى الوظيفي = قالب صلاحيات موحّد. المصدر الوحيد لتنظيم صلاحيات المستخدم."""
    _name = 'care.job.role'
    _description = 'مسمّى وظيفي (قالب صلاحيات)'
    _order = 'sequence, id'

    name = fields.Char(string='المسمّى', required=True, translate=True)
    name_en = fields.Char(string='Title (EN)')
    code = fields.Char(string='الرمز', index=True)
    sequence = fields.Integer(default=10)
    tier = fields.Selection(TIERS, string='الطبقة', default='officer', required=True)
    active = fields.Boolean(default=True)

    # نطاق البيانات
    data_scope = fields.Selection(
        [('all', 'كل الشركة'), ('own', 'مشاريعه المعيّنة فقط')],
        string='نطاق البيانات', default='all', required=True,
        help='own = تُولَّد record rules تحصر رؤيته في مشاريعه.')
    is_readonly = fields.Boolean(string='قراءة فقط (افتراضيًّا)')
    can_approve = fields.Boolean(string='يملك صلاحية اعتماد')
    description = fields.Text(string='الوصف / المهام')

    # الربط بمجموعات أودو الفعلية (تُولَّد/تُدار من المنظومة — لا يُسنَد المستخدم يدويًّا)
    odoo_group_ids = fields.Many2many(
        'res.groups', 'care_role_group_rel', 'role_id', 'group_id',
        string='مجموعات أودو المقابلة',
        help='المجموعات الفعلية التي يرِثها المستخدم عند إسناده لهذا المسمّى.')
    perm_line_ids = fields.One2many('care.role.perm', 'role_id', string='مصفوفة الصلاحيات')

    user_ids = fields.Many2many('res.users', 'care_user_role_rel', 'role_id', 'user_id',
                                string='المستخدمون بهذا المسمّى')
    user_count = fields.Integer(string='عدد المستخدمين', compute='_compute_counts')
    group_count = fields.Integer(string='عدد المجموعات', compute='_compute_counts')

    @api.depends('user_ids', 'odoo_group_ids')
    def _compute_counts(self):
        for r in self:
            r.user_count = len(r.user_ids)
            r.group_count = len(r.odoo_group_ids)

    _sql_constraints = [('code_uniq', 'unique(code)', 'رمز المسمّى يجب أن يكون فريدًا.')]

    def action_preview(self):
        """معاينة آمنة (dry-run): ماذا سيحصل عليه كل مستخدم بهذا المسمّى — دون أي تعديل إنتاجي."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('معاينة: %s') % self.name,
            'res_model': 'res.users',
            'domain': [('id', 'in', self.user_ids.ids)],
            'view_mode': 'tree,form',
            'target': 'current',
        }


MODULE_AREAS = [
    ('hr', 'الموارد البشرية'), ('payroll', 'الرواتب'), ('procurement', 'المشتريات والمناقصات'),
    ('projects', 'المشاريع'), ('fleet', 'الأسطول والكراج'), ('housing', 'السكنات'),
    ('finance', 'المالية والقيود'), ('approvals', 'مركز الموافقات'), ('sales', 'المبيعات'),
    ('marketing', 'التسويق'), ('legal', 'القانونية'), ('other', 'أخرى'),
]


class CareRolePerm(models.Model):
    """سطر في مصفوفة الصلاحيات: المسمّى × مجال موديول → مستوى (لا شيء/قراءة/كتابة/اعتماد)."""
    _name = 'care.role.perm'
    _description = 'صلاحية مسمّى على موديول'
    _order = 'role_id, area'

    role_id = fields.Many2one('care.job.role', string='المسمّى', required=True, ondelete='cascade')
    area = fields.Selection(MODULE_AREAS, string='المجال', required=True)
    level = fields.Selection(
        [('none', '—'), ('read', 'قراءة'), ('write', 'قراءة + كتابة'), ('approve', 'اعتماد')],
        string='المستوى', default='none', required=True)

    _sql_constraints = [('role_area_uniq', 'unique(role_id, area)',
                         'لكل مسمّى سطر واحد لكل مجال.')]
