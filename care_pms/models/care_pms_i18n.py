# -*- coding: utf-8 -*-
"""Arabic (ar_001) translations for care_pms, keeping English source."""
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)
AR = 'ar_001'

FIELDS = {
    'project.task': {
        'task_kind': 'النوع', 'pms_category_id': 'البند/الفئة', 'pms_department_id': 'الإدارة',
        'task_group_id': 'مجموعة التاسكات', 'is_overdue': 'متأخّر', 'forward_to_id': 'إحالة إلى',
        'forward_from_id': 'أحالها', 'forward_state': 'حالة الإحالة', 'forward_reason': 'سبب الإحالة',
    },
    'project.project': {
        'pms_department_id': 'الإدارة', 'project_manager_id': 'مدير المشروع', 'pms_state': 'حالة المشروع',
        'experience_ids': 'العقود', 'worker_count': 'العمال', 'vehicle_count': 'السيارات',
        'fuel_count': 'المحروقات', 'material_count': 'المخزون', 'portal_user_ids': 'مستخدمو البورتال',
        'pms_revenue': 'الإيراد الشهري', 'pms_labor_cost': 'تكلفة العمالة', 'pms_fleet_cost': 'تكلفة الأسطول',
        'pms_petty_spent': 'مصروف العُهد', 'pms_total_cost': 'إجمالي التكلفة', 'pms_margin': 'الهامش',
        'pms_margin_pct': 'نسبة الهامش %', 'sla_resolution_hours': 'مهلة SLA (ساعة)',
        'sla_compliance_pct': 'التزام SLA %', 'risk_score': 'درجة الخطر', 'risk_level': 'مستوى الخطر',
    },
    'care.pms.task.template': {'name': 'العنوان', 'project_id': 'المشروع', 'pms_category_id': 'البند',
                              'task_kind': 'النوع', 'user_ids': 'المسند إليهم', 'interval_number': 'التكرار كل',
                              'interval_type': 'الوحدة', 'next_date': 'التوليد القادم',
                              'deadline_offset': 'المهلة (+أيام)', 'generated_count': 'المُولّد'},
    'care.task.category': {'name': 'البند/الفئة', 'code': 'الرمز', 'task_count': 'عدد التاسكات'},
    'care.task.group': {'name': 'المجموعة', 'department_id': 'الإدارة', 'manager_id': 'المدير',
                        'member_ids': 'الأعضاء', 'is_private': 'خاصة (للأعضاء فقط)'},
    'care.task.forward': {'task_id': 'التاسك', 'from_user_id': 'من', 'to_user_id': 'إلى',
                          'reason': 'السبب', 'state': 'الحالة'},
    'care.pms.material': {'project_id': 'المشروع', 'name': 'الصنف', 'uom_name': 'الوحدة',
                          'min_qty': 'الحد الأدنى', 'received_qty': 'المستلَم', 'issued_qty': 'المسحوب',
                          'available_qty': 'المتاح', 'is_low': 'تحت الحد الأدنى'},
    'care.pms.delivery.note': {'name': 'المرجع', 'project_id': 'المشروع', 'location': 'الموقع',
                               'date': 'التاريخ', 'receiver_name': 'المستلِم', 'state': 'الحالة'},
    'care.pms.supply': {'name': 'المرجع', 'project_id': 'المشروع', 'source': 'المصدر / طلب الشراء',
                        'request_id': 'طلب الشراء', 'received_date': 'تاريخ الاستلام',
                        'date': 'التاريخ', 'receiver_name': 'استُلم بواسطة', 'state': 'الحالة'},
    'care.pms.supply.line': {'product_id': 'المنتج', 'name': 'الصنف', 'uom_name': 'الوحدة', 'qty': 'الكمية'},
    'care.pms.petty.cash': {'name': 'المرجع', 'project_id': 'المشروع', 'manager_id': 'العهدة باسم',
                            'amount': 'قيمة العهدة', 'spent': 'المصروف', 'remaining': 'المتبقّي', 'state': 'الحالة'},
    'care.pms.petty.cash.expense': {'name': 'البيان', 'category': 'التصنيف', 'amount': 'المبلغ',
                                    'attachment': 'المستند', 'note': 'وصف الحالة'},
    'care.pms.doc.request': {'name': 'المرجع', 'employee_id': 'العامل', 'department_id': 'الإدارة',
                             'project_id': 'المشروع', 'doc_type': 'نوع المستند', 'attachment': 'صورة المستند',
                             'description': 'ملاحظات', 'requested_by': 'مُقدّم الطلب', 'approver_id': 'المعتمِد',
                             'state': 'الحالة'},
}
SELECTIONS = {
    'project.task': {
        'task_kind': {'task': 'مهمة', 'memo': 'مذكرة', 'internal_letter': 'كتاب داخلي',
                      'internal_request': 'طلب داخلي', 'correspondence': 'مراسلة'},
        'forward_state': {'none': '—', 'pending': 'بانتظار القبول', 'accepted': 'مقبولة', 'rejected': 'مرفوضة'},
    },
    'project.project': {
        'pms_state': {'draft': 'مسودة', 'active': 'نشط', 'follow': 'يحتاج متابعة',
                      'overdue': 'متأخر', 'closed': 'مغلق'},
        'risk_level': {'low': 'منخفض', 'medium': 'متوسط', 'high': 'عالٍ'},
    },
    'care.task.forward': {'state': {'pending': 'بانتظار', 'accepted': 'مقبولة', 'rejected': 'مرفوضة'}},
    'care.pms.delivery.note': {'state': {'draft': 'مسودة', 'done': 'مؤكّد'}},
    'care.pms.petty.cash': {'state': {'draft': 'طلب (مسودة)', 'requested': 'طلب مُقدَّم',
                            'approved': 'معتمد', 'disbursed': 'مصروفة (نشطة)',
                            'settled': 'تسوية مُقدَّمة', 'closed': 'مغلقة'}},
    'care.pms.petty.cash.expense': {'category': {'maintenance': 'صيانة', 'fuel': 'محروقات',
                                    'transport': 'مواصلات', 'supplies': 'مستلزمات', 'misc': 'نثريات'}},
    'care.pms.doc.request': {
        'doc_type': {'civil_id': 'البطاقة المدنية', 'passport': 'جواز السفر', 'photo': 'صورة شخصية',
                     'work_permit': 'تصريح عمل', 'residence': 'الإقامة', 'medical': 'طبي', 'other': 'أخرى'},
        'state': {'draft': 'مسودة', 'submitted': 'مقدّم', 'approved': 'معتمد', 'rejected': 'مرفوض'}},
    'care.pms.task.template': {
        'task_kind': {'task': 'مهمة', 'memo': 'مذكرة', 'internal_letter': 'كتاب داخلي',
                      'internal_request': 'طلب داخلي', 'correspondence': 'مراسلة'},
        'interval_type': {'days': 'أيام', 'weeks': 'أسابيع', 'months': 'أشهر'}},
}


class PmsI18n(models.AbstractModel):
    _name = 'care.pms.i18n'
    _description = 'care_pms Arabic i18n'

    @api.model
    def apply_ar(self):
        lang = self.env['res.lang'].with_context(active_test=False).search([('code', '=', AR)], limit=1)
        if lang and not lang.active:
            lang.active = True
        Fields = self.env['ir.model.fields']
        for model, fmap in FIELDS.items():
            for fname, label in fmap.items():
                rec = Fields.search([('model', '=', model), ('name', '=', fname)], limit=1)
                if rec:
                    try:
                        rec.with_context(lang=AR).field_description = label
                    except Exception as e:
                        _logger.debug('i18n %s.%s: %s', model, fname, e)
        for model, smap in SELECTIONS.items():
            for fname, values in smap.items():
                field = Fields.search([('model', '=', model), ('name', '=', fname)], limit=1)
                if not field:
                    continue
                for value, label in values.items():
                    sel = self.env['ir.model.fields.selection'].search(
                        [('field_id', '=', field.id), ('value', '=', value)], limit=1)
                    if sel:
                        try:
                            sel.with_context(lang=AR).name = label
                        except Exception as e:
                            _logger.debug('i18n sel %s.%s.%s: %s', model, fname, value, e)
        _logger.info('care_pms: Arabic translations applied')
        return True
