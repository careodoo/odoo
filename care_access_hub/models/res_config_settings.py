# -*- coding: utf-8 -*-
from odoo import fields, models

# الأفكار المتقدّمة كخيارات تُفعَّل / تُعطَّل على مستوى الشركة.


class ResCompany(models.Model):
    _inherit = 'res.company'

    ah_sod = fields.Boolean('فصل الواجبات (منع مُنشئ المستند من اعتماده)', default=True)
    ah_thresholds = fields.Boolean('حدود مبالغ الاعتماد (تصعيد تلقائي)', default=True)
    ah_delegation = fields.Boolean('التفويض المؤقّت (الإنابة)', default=True)
    ah_field_mask = fields.Boolean('إخفاء الحقول الحسّاسة حسب المسمّى', default=True)
    ah_simulator = fields.Boolean('محاكي الصلاحيات (ماذا يستطيع المستخدم؟)', default=True)
    ah_auto_scope = fields.Boolean('نطاق البيانات التلقائي (record rules للمشاريع)', default=True)
    ah_audit = fields.Boolean('سجلّ تدقيق كامل للصلاحيات والاعتماد', default=True)
    ah_odoo_sync = fields.Boolean('مزامنة أودو التلقائية (توليد المجموعات/القواعد)', default=False)
    ah_emergency = fields.Boolean('صلاحية الطوارئ المؤقّتة (break-glass)', default=False)
    ah_heatmap = fields.Boolean('الخريطة الحرارية لاختناقات الاعتماد', default=True)
    ah_bulk_assign = fields.Boolean('الإسناد الجماعي بالمسمّى', default=True)
    ah_temp_grant = fields.Boolean('صلاحيات مؤقّتة بتاريخ انتهاء', default=True)
    ah_stage_approval = fields.Boolean('الاعتماد بمرحلة محدّدة (لا ثنائي)', default=True)
    ah_multi_approver = fields.Boolean('عدّة معتمِدين لكل مرحلة', default=True)
    ah_notify_prefs = fields.Boolean('لوحة إشعارات الموظف (داخلي + بورتال)', default=True)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ah_sod = fields.Boolean(related='company_id.ah_sod', readonly=False)
    ah_thresholds = fields.Boolean(related='company_id.ah_thresholds', readonly=False)
    ah_delegation = fields.Boolean(related='company_id.ah_delegation', readonly=False)
    ah_field_mask = fields.Boolean(related='company_id.ah_field_mask', readonly=False)
    ah_simulator = fields.Boolean(related='company_id.ah_simulator', readonly=False)
    ah_auto_scope = fields.Boolean(related='company_id.ah_auto_scope', readonly=False)
    ah_audit = fields.Boolean(related='company_id.ah_audit', readonly=False)
    ah_odoo_sync = fields.Boolean(related='company_id.ah_odoo_sync', readonly=False)
    ah_emergency = fields.Boolean(related='company_id.ah_emergency', readonly=False)
    ah_heatmap = fields.Boolean(related='company_id.ah_heatmap', readonly=False)
    ah_bulk_assign = fields.Boolean(related='company_id.ah_bulk_assign', readonly=False)
    ah_temp_grant = fields.Boolean(related='company_id.ah_temp_grant', readonly=False)
    ah_stage_approval = fields.Boolean(related='company_id.ah_stage_approval', readonly=False)
    ah_multi_approver = fields.Boolean(related='company_id.ah_multi_approver', readonly=False)
    ah_notify_prefs = fields.Boolean(related='company_id.ah_notify_prefs', readonly=False)
