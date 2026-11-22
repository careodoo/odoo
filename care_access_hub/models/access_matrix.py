# -*- coding: utf-8 -*-
# مصفوفة الصلاحيات الغنية (تبويب «مصفوفة الصلاحيات» بالموكاب):
#  - سطر لكل (مسمّى × مودل) بمستوى: — / قراءة / قراءة+كتابة.  (الاعتماد مستقلّ في مراحل الاعتماد.)
#  - إخفاء الحقول: قناع على مستوى الحقل لكل مسمّى.
#  - الترحيل الفعلي: اشتقاق المستوى من ACL مجموعات المسمّى الحالية (الوضع القائم → النظام الجديد).
from odoo import api, fields, models, _

# المصفوفة المُنسَّقة: (عنوان الموديول, [(مودل تقني, اسم عربي), ...]) — تُطابق شجرة الموكاب
MATRIX = [
    ('الموارد البشرية', [('hr.employee', 'الموظف'), ('hr.contract', 'العقد'), ('hr.leave', 'طلب إجازة')]),
    ('الرواتب', [('care.payroll', 'كشف الراتب'), ('care.payslip', 'قسيمة الراتب')]),
    ('نهاية الخدمة', [('care.eos', 'طلب نهاية خدمة'), ('care.eos.request', 'تسوية نهاية خدمة')]),
    ('الجوازات والإقامات', [('care.passport.request', 'طلب جواز'), ('care.permit.request', 'طلب تصريح')]),
    ('المشتريات والمناقصات', [('purchase.order', 'أمر الشراء'), ('purchase.tender', 'المناقصة'),
                              ('purchase.request', 'طلب الشراء')]),
    ('عروض الأسعار', [('care.proposal', 'عرض السعر')]),
    ('المشاريع', [('project.project', 'المشروع'), ('project.task', 'المهمة'), ('care.timesheet', 'التايم شيت')]),
    ('العمل الإضافي', [('care.extra.work', 'العمل الإضافي'), ('overtime.request', 'طلب إضافي')]),
    ('الأسطول والكراج', [('fleet.vehicle', 'المركبة'), ('fleet.vehicle.log.services', 'الصيانة'),
                         ('care.vehicle.handover', 'محضر الاستلام')]),
    ('السكنات', [('care.housing', 'السكن'), ('care.housing.room', 'الغرفة/السرير')]),
    ('المالية والقيود', [('account.move', 'القيد المحاسبي'), ('account.payment', 'الدفعة')]),
    ('العُهد والمصروفات', [('care.pms.petty.cash', 'العهدة النقدية'), ('care.penalty', 'الجزاء')]),
    ('مركز الموافقات', [('care.approval.center', 'طلب الاعتماد')]),
    ('التصاريح الحكومية', [('care.gov.custody', 'عهدة حكومية'), ('care.defense.permit', 'تصريح دفاع')]),
    ('الشكاوى التأديبية', [('care.complaint', 'شكوى تأديبية')]),
]


class CareRoleModelPerm(models.Model):
    """مستوى صلاحية المسمّى على مودل مُعيّن — المصفوفة الغنية."""
    _name = 'care.role.model.perm'
    _description = 'صلاحية مسمّى على مودل'
    _order = 'sequence, module, model_label'

    role_id = fields.Many2one('care.job.role', string='المسمّى', required=True, ondelete='cascade', index=True)
    module = fields.Char(string='الموديول')
    model_name = fields.Char(string='المودل (تقني)', required=True)
    model_label = fields.Char(string='المودل')
    sequence = fields.Integer(default=10)
    level = fields.Selection(
        [('0', '— بلا'), ('1', 'قراءة'), ('2', 'قراءة + كتابة')],
        string='المستوى', default='0', required=True)
    mask_count = fields.Integer(string='حقول مخفية', compute='_compute_mask_count')

    _sql_constraints = [('role_model_uniq', 'unique(role_id, model_name)',
                         'المودل مُعرَّف مسبقًا لهذا المسمّى.')]

    def _compute_mask_count(self):
        Mask = self.env['care.role.field.mask'].sudo()
        for r in self:
            r.mask_count = Mask.search_count(
                [('role_id', '=', r.role_id.id), ('model_name', '=', r.model_name), ('hidden', '=', True)])

    def action_fields(self):
        """فتح إدارة إخفاء حقول هذا المودل لهذا المسمّى."""
        self.ensure_one()
        self.env['care.role.field.mask']._ensure_fields(self.role_id, self.model_name, self.model_label)
        return {
            'type': 'ir.actions.act_window', 'name': _('حقول: %s') % (self.model_label or self.model_name),
            'res_model': 'care.role.field.mask', 'view_mode': 'tree',
            'domain': [('role_id', '=', self.role_id.id), ('model_name', '=', self.model_name)],
            'target': 'new', 'context': {'default_role_id': self.role_id.id,
                                         'default_model_name': self.model_name},
        }


class CareRoleFieldMask(models.Model):
    """إخفاء/قفل حقل عن مسمّى (قناع على مستوى الحقل)."""
    _name = 'care.role.field.mask'
    _description = 'إخفاء حقل عن مسمّى'
    _order = 'model_name, field_label'

    role_id = fields.Many2one('care.job.role', string='المسمّى', required=True, ondelete='cascade', index=True)
    model_name = fields.Char(string='المودل', required=True, index=True)
    field_name = fields.Char(string='الحقل (تقني)', required=True)
    field_label = fields.Char(string='الحقل')
    hidden = fields.Boolean(string='مخفي / مقفل 🔒')

    _sql_constraints = [('role_field_uniq', 'unique(role_id, model_name, field_name)', 'مُعرَّف مسبقًا.')]

    @api.model
    def _ensure_fields(self, role, model_name, model_label=None):
        """يُنشئ صفوف الحقول المرئية للمودل إن لم تكن موجودة (مرّة واحدة)."""
        M = self.env.get(model_name)
        if M is None:
            return
        existing = set(self.sudo().search(
            [('role_id', '=', role.id), ('model_name', '=', model_name)]).mapped('field_name'))
        rows = []
        for fname, f in M._fields.items():
            if fname in existing or f.automatic or fname.startswith('_'):
                continue
            # حقول المستخدم المرئية فقط (نتجاهل التقنية/المحوسبة بلا تخزين الكثيفة)
            if f.type in ('one2many', 'many2many') and not f.store:
                continue
            rows.append({'role_id': role.id, 'model_name': model_name,
                         'field_name': fname, 'field_label': (f.string or fname)[:120], 'hidden': False})
        if rows:
            self.sudo().create(rows)
