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
    perm_line_ids = fields.One2many('care.role.perm', 'role_id', string='مصفوفة الصلاحيات (مناطق)')
    model_perm_ids = fields.One2many('care.role.model.perm', 'role_id', string='مصفوفة الصلاحيات (مودلز)')

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

    # ---------- الترحيل الفعلي: اشتقاق المصفوفة من المجموعات الحالية ----------
    def _level_from_groups(self, groups, model_name):
        """مستوى المسمّى على مودل، مُشتقّ من ACL مجموعاته الحالية:
        2=كتابة إن منحت أي مجموعة write/create، 1=قراءة إن منحت read، 0=بلا."""
        if not groups:
            return '0'
        acls = self.env['ir.model.access'].sudo().search([
            ('model_id.model', '=', model_name), ('group_id', 'in', groups.ids)])
        if not acls:
            return '0'
        if any(a.perm_write or a.perm_create for a in acls):
            return '2'
        if any(a.perm_read for a in acls):
            return '1'
        return '0'

    def action_derive_matrix(self):
        """يملأ مصفوفة المودلز من الوضع الحالي (مجموعات المسمّى) — ترحيل فعلي، بلا تعديل إنتاجي."""
        from .access_matrix import MATRIX
        Line = self.env['care.role.model.perm'].sudo()
        for role in self:
            groups = role.odoo_group_ids
            existing = {l.model_name: l for l in role.model_perm_ids}
            seq = 0
            for module, models_ in MATRIX:
                for mname, mlabel in models_:
                    seq += 1
                    if self.env.get(mname) is None:
                        continue  # المودل غير مُثبّت — نتخطّاه
                    lvl = role._level_from_groups(groups, mname)
                    vals = {'module': module, 'model_label': mlabel, 'sequence': seq, 'level': lvl}
                    if mname in existing:
                        existing[mname].write(vals)
                    else:
                        vals.update({'role_id': role.id, 'model_name': mname})
                        Line.create(vals)
        return True

    @api.model
    def cron_or_action_derive_all(self):
        """اشتقاق مصفوفة كل المسمّيات (زرّ/سيرفر أكشن)."""
        self.search([]).action_derive_matrix()
        return True


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
