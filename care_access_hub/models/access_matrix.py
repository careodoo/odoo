# -*- coding: utf-8 -*-
# مصفوفة الصلاحيات الغنية (تبويب «مصفوفة الصلاحيات» بالموكاب):
#  - سطر لكل (مسمّى × مودل) بمستوى: — / قراءة / قراءة+كتابة.  (الاعتماد مستقلّ في مراحل الاعتماد.)
#  - إخفاء الحقول: قناع على مستوى الحقل لكل مسمّى.
#  - الترحيل الفعلي: اشتقاق المستوى من ACL مجموعات المسمّى الحالية (الوضع القائم → النظام الجديد).
from odoo import api, fields, models, _

# موديولات تقنية تُستبعَد من المصفوفة (ليست أعمالًا)
_EXCL_MOD = {
    'base', 'web', 'web_editor', 'web_tour', 'web_unsplash', 'mail', 'bus', 'iap', 'base_setup',
    'base_import', 'base_vat', 'base_address_city', 'base_address_extended', 'phone_validation',
    'digest', 'resource', 'auth_signup', 'auth_totp', 'portal', 'http_routing', 'website',
    'social_media', 'utm', 'link_tracker', 'google_gmail', 'microsoft_account', 'spreadsheet',
    'spreadsheet_dashboard', 'barcodes', 'onboarding', 'uom',
}
_EXCL_PREFIX = ('ir.', 'base.', 'bus.', 'mail.', 'web_', 'website', 'res.lang', 'res.currency',
                'report.', 'spreadsheet', 'digest.', 'iap.', 'auth_', 'format.', 'utm.', 'link.tracker')


def build_matrix_tree(env):
    """يبني شجرة (موديول → مودلز أعماله) ديناميكيًّا من كل الموديولات المُثبّتة:
    المودلز المواجهة للمستخدم فقط (لها نافذة إجراء)، مجمّعة بالموديول المُعرِّف، مستبعِدًا التقنية."""
    Mod = env['ir.module.module'].sudo()
    installed = Mod.search([('state', '=', 'installed')])
    modlabel = {m.name: (m.shortdesc or m.name) for m in installed}
    installed_names = set(modlabel)
    # الموديول المُعرِّف لكل مودل عبر ir.model_data
    model_mod = {}
    for d in env['ir.model.data'].sudo().search([('model', '=', 'ir.model')]):
        model_mod.setdefault(d.res_id, d.module)
    # المودلز المواجهة للمستخدم (لها act_window)
    aw_models = set(env['ir.actions.act_window'].sudo().search([]).mapped('res_model'))
    tree = {}
    for m in env['ir.model'].sudo().search([('transient', '=', False)]):
        tech = m.model
        if tech not in aw_models:
            continue
        if tech.startswith(_EXCL_PREFIX):
            continue
        mod = model_mod.get(m.id)
        if not mod or mod not in installed_names or mod in _EXCL_MOD:
            continue
        tree.setdefault(mod, []).append((tech, m.name))
    # قائمة مرتّبة: care_* أولًا ثم الباقي، وداخل كل موديول بالاسم
    def _key(mod):
        return (0 if mod.startswith('care') else 1, modlabel.get(mod, mod))
    out = []
    for mod in sorted(tree, key=_key):
        models_ = sorted(set(tree[mod]), key=lambda x: x[1])
        out.append((modlabel.get(mod, mod), models_))
    return out


# المصفوفة المُنسَّقة (احتياطية — تُستخدم إن فشل البناء الديناميكي)
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
        if not rows:
            return
        # آمن للسباق: استدعاءان متزامنان (نقرتان سريعتان/تحديث دوري) قد يحاولان الإدراج معًا
        # ⇒ ينتهك القيد الفريد. نُدرج داخل savepoint، وعند التكرار نُدرج المفقود فقط فردًا فردًا.
        try:
            with self.env.cr.savepoint():
                self.sudo().create(rows)
        except Exception:
            now = set(self.sudo().search(
                [('role_id', '=', role.id), ('model_name', '=', model_name)]).mapped('field_name'))
            for v in rows:
                if v['field_name'] in now:
                    continue
                try:
                    with self.env.cr.savepoint():
                        self.sudo().create([v])
                except Exception:
                    pass
