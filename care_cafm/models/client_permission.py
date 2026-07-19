# -*- coding: utf-8 -*-
"""Per-client permissions.

Every client write in the API used to hang off one boolean called
``cafm_can_add_workers``. Turning it on to let a client log a service request
also let them delete buildings, approve invoices and broadcast notifications to
every worker on site — and turning it off to prevent that also took away the
request form. One switch, twenty-five very different powers.

This replaces it with a real matrix: each capability is named, defaults to
something sensible, and is granted per client. The old boolean stays as the
fallback for clients nobody has configured yet, so nothing silently changes
permission the day this ships.
"""
from odoo import api, fields, models, _

# code -> (label, help, default_on, group)
PERMISSIONS = [
    # ---- requesting work ----
    ('request_create', 'إنشاء طلب خدمة',
     'تقديم طلب خدمة جديد يتحوّل لاحقًا إلى أمر عمل.', True, 'work'),
    ('workorder_create', 'إنشاء أمر عمل مباشرة',
     'تخطّي مرحلة الطلب وإنشاء أمر عمل جاهز للإسناد.', False, 'work'),
    ('workorder_verify', 'اعتماد الأعمال المنجزة',
     'قبول أو رفض العمل بعد تنفيذه.', True, 'work'),
    ('schedule_manage', 'إدارة الجدولة والصيانة الوقائية',
     'إنشاء وإيقاف الجداول الدورية وخطط الصيانة الوقائية.', False, 'work'),

    # ---- quality ----
    ('observation_create', 'تسجيل ملاحظة جودة',
     'رفع ملاحظة على مستوى الخدمة مع صور وفيديو.', True, 'quality'),
    ('observation_convert', 'تحويل الملاحظة إلى أمر عمل',
     'تصعيد الملاحظة مباشرة إلى عمل مُسنَد.', False, 'quality'),

    # ---- assets and structure ----
    ('asset_manage', 'إدارة الأصول',
     'إضافة وتعديل وحذف الأصول والمعدّات.', False, 'assets'),
    ('structure_manage', 'إدارة المباني والأدوار والمواقع',
     'تعديل الهيكل المكاني للمرفق.', False, 'assets'),

    # ---- people ----
    ('worker_add', 'إضافة عمّال',
     'إضافة عامل جديد وإسناده لفريق.', False, 'people'),
    ('team_manage', 'إدارة الفرق',
     'إنشاء الفرق وتعديل أعضائها.', False, 'people'),
    ('notify_send', 'إرسال إشعارات للعمّال',
     'بثّ إشعار لفريق أو لمجموعة عمّال.', False, 'people'),

    # ---- money ----
    ('invoice_approve', 'اعتماد الفواتير',
     'قبول أو رفض الفواتير المرفوعة للعميل.', False, 'money'),
    ('shop_order', 'الطلب من المتجر',
     'إنشاء طلبات شراء من متجر العميل.', True, 'money'),

    # ---- services ----
    ('hospitality_order', 'طلبات الضيافة',
     'طلب المشروبات والضيافة من داخل النظام.', True, 'services'),
    ('inventory_issue', 'صرف المواد من المخزون',
     'صرف المستهلكات للعمّال من مخازن المشروع.', False, 'services'),
    ('inventory_policy', 'ضبط سياسة صرف المواد',
     'تحديد المواد المسموح للعمّال صرفها وحدودها.', False, 'services'),
]

GROUPS = {
    'work': 'الأعمال والطلبات', 'quality': 'الجودة', 'assets': 'الأصول والمباني',
    'people': 'الفِرَق والعمّال', 'money': 'المالية والمتجر', 'services': 'الخدمات',
}

# Capabilities the legacy boolean used to imply. A client who had it stays
# exactly as powerful as before; a client who did not keeps the safe defaults.
LEGACY_IMPLIED = [c for c, _l, _h, d, _g in PERMISSIONS if not d]


class CafmClientPermission(models.Model):
    """One row per (client, capability) that has been explicitly decided.
    Absence of a row means "fall back to the default"."""
    _name = 'care.cafm.client.permission'
    _description = 'صلاحية عميل'
    _order = 'client_id, code'

    client_id = fields.Many2one('care.cafm.client', string='العميل', required=True,
                                ondelete='cascade', index=True)
    code = fields.Selection([(c, l) for c, l, _h, _d, _g in PERMISSIONS],
                            string='الصلاحية', required=True)
    allowed = fields.Boolean(string='مسموح', default=True)

    _sql_constraints = [('client_code_uniq', 'unique(client_id, code)',
                         'الصلاحية مُعرّفة مسبقًا لهذا العميل.')]


class CafmClientPermissionMixin(models.AbstractModel):
    """Grafted onto care.cafm.client — kept apart so the permission logic reads
    in one place instead of being buried in the org model."""
    _name = 'care.cafm.client.permission.mixin'
    _description = 'صلاحيات العميل'

    permission_ids = fields.One2many('care.cafm.client.permission', 'client_id',
                                     string='الصلاحيات')
    permission_summary = fields.Char(string='الصلاحيات الممنوحة',
                                     compute='_compute_permission_summary')

    def _compute_permission_summary(self):
        labels = {c: l for c, l, _h, _d, _g in PERMISSIONS}
        for rec in self:
            granted = [labels[c] for c in rec.granted_codes() if c in labels]
            rec.permission_summary = ('%s صلاحية: %s' % (len(granted), '، '.join(granted[:4]))
                                      + ('…' if len(granted) > 4 else '')) if granted else 'لا صلاحيات'


    # ---- one boolean per capability, so the matrix is an ordinary form ----
    perm_request_create = fields.Boolean(
        string='إنشاء طلب خدمة', compute='_compute_perm_flags', inverse='_inverse_perm_flags',
        help='تقديم طلب خدمة جديد يتحوّل لاحقًا إلى أمر عمل.', store=False)
    perm_workorder_create = fields.Boolean(
        string='إنشاء أمر عمل مباشرة', compute='_compute_perm_flags', inverse='_inverse_perm_flags',
        help='تخطّي مرحلة الطلب وإنشاء أمر عمل جاهز للإسناد.', store=False)
    perm_workorder_verify = fields.Boolean(
        string='اعتماد الأعمال المنجزة', compute='_compute_perm_flags', inverse='_inverse_perm_flags',
        help='قبول أو رفض العمل بعد تنفيذه.', store=False)
    perm_schedule_manage = fields.Boolean(
        string='إدارة الجدولة والصيانة الوقائية', compute='_compute_perm_flags', inverse='_inverse_perm_flags',
        help='إنشاء وإيقاف الجداول الدورية وخطط الصيانة الوقائية.', store=False)
    perm_observation_create = fields.Boolean(
        string='تسجيل ملاحظة جودة', compute='_compute_perm_flags', inverse='_inverse_perm_flags',
        help='رفع ملاحظة على مستوى الخدمة مع صور وفيديو.', store=False)
    perm_observation_convert = fields.Boolean(
        string='تحويل الملاحظة إلى أمر عمل', compute='_compute_perm_flags', inverse='_inverse_perm_flags',
        help='تصعيد الملاحظة مباشرة إلى عمل مُسنَد.', store=False)
    perm_asset_manage = fields.Boolean(
        string='إدارة الأصول', compute='_compute_perm_flags', inverse='_inverse_perm_flags',
        help='إضافة وتعديل وحذف الأصول والمعدّات.', store=False)
    perm_structure_manage = fields.Boolean(
        string='إدارة المباني والأدوار والمواقع', compute='_compute_perm_flags', inverse='_inverse_perm_flags',
        help='تعديل الهيكل المكاني للمرفق.', store=False)
    perm_worker_add = fields.Boolean(
        string='إضافة عمّال', compute='_compute_perm_flags', inverse='_inverse_perm_flags',
        help='إضافة عامل جديد وإسناده لفريق.', store=False)
    perm_team_manage = fields.Boolean(
        string='إدارة الفرق', compute='_compute_perm_flags', inverse='_inverse_perm_flags',
        help='إنشاء الفرق وتعديل أعضائها.', store=False)
    perm_notify_send = fields.Boolean(
        string='إرسال إشعارات للعمّال', compute='_compute_perm_flags', inverse='_inverse_perm_flags',
        help='بثّ إشعار لفريق أو لمجموعة عمّال.', store=False)
    perm_invoice_approve = fields.Boolean(
        string='اعتماد الفواتير', compute='_compute_perm_flags', inverse='_inverse_perm_flags',
        help='قبول أو رفض الفواتير المرفوعة للعميل.', store=False)
    perm_shop_order = fields.Boolean(
        string='الطلب من المتجر', compute='_compute_perm_flags', inverse='_inverse_perm_flags',
        help='إنشاء طلبات شراء من متجر العميل.', store=False)
    perm_hospitality_order = fields.Boolean(
        string='طلبات الضيافة', compute='_compute_perm_flags', inverse='_inverse_perm_flags',
        help='طلب المشروبات والضيافة من داخل النظام.', store=False)
    perm_inventory_issue = fields.Boolean(
        string='صرف المواد من المخزون', compute='_compute_perm_flags', inverse='_inverse_perm_flags',
        help='صرف المستهلكات للعمّال من مخازن المشروع.', store=False)
    perm_inventory_policy = fields.Boolean(
        string='ضبط سياسة صرف المواد', compute='_compute_perm_flags', inverse='_inverse_perm_flags',
        help='تحديد المواد المسموح للعمّال صرفها وحدودها.', store=False)

    def _compute_perm_flags(self):
        for rec in self:
            granted = rec.granted_codes()
            for code, _l, _h, _d, _g in PERMISSIONS:
                rec['perm_%s' % code] = code in granted

    def _inverse_perm_flags(self):
        for rec in self:
            for code, _l, _h, _d, _g in PERMISSIONS:
                rec.set_permission(code, bool(rec['perm_%s' % code]))

    def granted_codes(self):
        """Every capability this client currently holds."""
        self.ensure_one()
        explicit = {p.code: p.allowed for p in self.permission_ids}
        legacy = bool(self.can_add_workers)
        out = set()
        for code, _l, _h, default, _g in PERMISSIONS:
            if code in explicit:
                if explicit[code]:
                    out.add(code)
            elif default or (legacy and code in LEGACY_IMPLIED):
                out.add(code)
        return out

    def can(self, code):
        self.ensure_one()
        return code in self.granted_codes()

    def set_permission(self, code, allowed):
        """Explicitly decide one capability (used by the admin screens)."""
        self.ensure_one()
        Perm = self.env['care.cafm.client.permission'].sudo()
        rec = Perm.search([('client_id', '=', self.id), ('code', '=', code)], limit=1)
        if rec:
            rec.allowed = bool(allowed)
        else:
            Perm.create({'client_id': self.id, 'code': code, 'allowed': bool(allowed)})
        return True

    def action_grant_all(self):
        for rec in self:
            for code, _l, _h, _d, _g in PERMISSIONS:
                rec.set_permission(code, True)
        return True

    def action_revoke_all(self):
        for rec in self:
            for code, _l, _h, _d, _g in PERMISSIONS:
                rec.set_permission(code, False)
        return True

    @api.model
    def permission_catalogue(self):
        """The full matrix, for the admin UI and the /client/permissions API."""
        return [{'code': c, 'label': l, 'help': h, 'default': d,
                 'group': g, 'group_label': GROUPS.get(g, g)}
                for c, l, h, d, g in PERMISSIONS]
