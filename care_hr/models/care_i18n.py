# -*- coding: utf-8 -*-
"""Arabic (ar_001) translations for the care_hr UI.

Standing rule: every care module must be fully translated to Arabic while
keeping the English source (English for English users, Arabic for Arabic
users). This routine writes ar_001 translations for menus, field labels and
selection values of the care models. It is idempotent and called on every
module update via a <function> in data/care_i18n_data.xml. Extend the maps
below whenever new UI is added."""
from odoo import models, api

LANG = 'ar_001'

MENUS = {
    # billing / profitability
    'menu_care_client_billing': 'فوترة العميل',
    'menu_care_client_billing_scan': '↻ توليد فوترة الشهر',
    'menu_care_pnl': 'ربحية العقود',
    'menu_care_pnl_scan': '↻ تحديث الربحية',
    # welfare
    'menu_care_expense': 'المطالبات والنثريات',
    'menu_care_insurance': 'وثائق التأمين',
    'menu_care_gosi': 'التأمينات الاجتماعية (GOSI)',
    # analytics
    'menu_care_data_quality': 'جودة البيانات',
    'menu_care_data_quality_scan': '↻ فحص جودة البيانات',
    'menu_care_exceptions': 'الاستثناءات',
    'menu_care_attrition': 'تحليل التسرّب',
    'menu_care_attrition_risk': 'العمال المعرّضون للخطر',
    'menu_care_attrition_scan': '↻ تحديث التسرّب',
    # governance
    'menu_care_hse': 'حوادث السلامة (HSE)',
    'menu_care_equipment': 'المعدات والأصول',
    'menu_care_wfp': 'تخطيط القوى العاملة',
    # recruitment / training integration
    'menu_care_applicants': 'المتقدّمون (التوظيف)',
    'menu_care_jobs': 'الوظائف الشاغرة',
    'menu_care_training': 'أكاديمية التدريب',
    # ---- older care_hr menus ----
    'absence_menu': 'الغياب', 'absence_root': 'الغياب',
    'care_hr_leave_menu': 'إجازة سريعة',
    'clearance_menu': 'إخلاء الطرف', 'clearance_root': 'إخلاء الطرف',
    'joining_menu': 'المباشرة', 'joining_root': 'المباشرة',
    'leave_return_menu': 'العودة من الإجازة', 'leave_return_root': 'العودة من الإجازة',
    'menu_care_access_profile': 'ملفات الصلاحيات',
    'menu_care_allowance': 'البدلات', 'menu_care_allowance_type': 'أنواع البدلات',
    'menu_care_announcement': 'الإعلانات واللوائح',
    'menu_care_archive_root': 'أرشيف السفر',
    'menu_care_bonus': 'المكافآت',
    'menu_care_coverage_alert': 'مراقب التغطية',
    'menu_care_custody': 'سجل العُهد',
    'menu_care_deployment': 'التمركز',
    'menu_care_eos': 'نهاية الخدمة',
    'menu_care_eos_liab': 'التزام نهاية الخدمة',
    'menu_care_eos_liab_scan': '↻ تحديث التزام نهاية الخدمة',
    'menu_care_gov_transaction': 'المعاملات الحكومية (المندوب)',
    'menu_care_grievance': 'التظلّمات',
    'menu_care_hr_admin_root': 'الشؤون الإدارية',
    'menu_care_hr_policy': 'لائحة الموارد البشرية (قانون العمل)',
    'menu_care_hr_relations_root': 'علاقات الموظفين',
    'menu_care_job_grade': 'الدرجات الوظيفية / شرائح الأجور',
    'menu_care_job_skill': 'متطلبات الوظيفة والفجوة',
    'menu_care_letter': 'الخطابات والشهادات',
    'menu_care_manpower_file': 'ملفات القوى العاملة (الشؤون)',
    'menu_care_movement': 'الحركات / النقل',
    'menu_care_passport': 'الجوازات',
    'menu_care_passport_movement': 'حركات الجوازات (صرف/إرجاع)',
    'menu_care_penalty': 'الجزاءات', 'menu_care_penalty_type': 'كتالوج الجزاءات',
    'menu_care_probation': 'فترة التجربة',
    'menu_care_quality': 'جودة العامل',
    'menu_care_request': 'مركز الطلبات',
    'menu_care_site_permit': 'تصاريح المواقع والأمن',
    'menu_care_skill_assessment': 'تقييم المهارات',
    'menu_care_skill_catalog': 'كتالوج المهارات',
    'menu_care_skill_endorsement': 'التزكيات',
    'menu_care_skill_type': 'أنواع المهارات',
    'menu_care_skills_cert': 'الشهادات',
    'menu_care_skills_dashboard': 'لوحة المهارات',
    'menu_care_skills_matrix': 'مصفوفة المهارات',
    'menu_care_skills_root': 'مركز المهارات',
    'menu_care_violation': 'المخالفات المرورية',
    'menu_care_violation_type': 'أنواع المخالفات',
    'menu_care_sla': 'مستوى تغطية المواقع (SLA)',
    'menu_care_sla_scan': '↻ احتساب SLA اليوم',
    'menu_care_loan': 'السلف والقروض',
    'menu_hostel_dashboard': 'داشبورد السكن',
    'menu_dept_link': 'ربط الأقسام بالمشاريع',
    'menu_dept_suggest': '↻ توليد الاقتراحات',
    'menu_dept_apply_strong': '✓ تطبيق المطابقات القوية',
}

ACTIONS = {
    'action_care_client_billing': 'فوترة العميل',
    'action_care_pnl': 'ربحية العقود',
    'action_care_expense': 'المطالبات والنثريات',
    'action_care_insurance': 'وثائق التأمين',
    'action_care_gosi': 'التأمينات الاجتماعية',
    'action_care_data_quality': 'جودة البيانات',
    'action_care_exceptions': 'الاستثناءات',
    'action_care_attrition': 'تحليل التسرّب',
    'action_care_attrition_risk': 'العمال المعرّضون للخطر',
    'action_care_applicants': 'المتقدّمون (التوظيف)',
    'action_care_jobs': 'الوظائف الشاغرة',
    'action_care_training': 'التدريب',
    'action_care_sla': 'مستوى تغطية المواقع (SLA)',
    'action_care_loan': 'السلف والقروض',
    'action_hostel_dashboard': 'داشبورد السكن',
}

# model -> {field_name: arabic_label}
FIELDS = {
    'care.client.billing': {
        'name': 'المرجع', 'project_id': 'المشروع', 'contract_id': 'العقد',
        'partner_id': 'العميل', 'date_from': 'من تاريخ', 'date_to': 'إلى تاريخ',
        'billing_basis': 'أساس الفوترة', 'price_type': 'نوع السعر', 'price_unit': 'السعر',
        'worker_count': 'عدد العمال', 'work_days': 'أيام العمل', 'amount': 'المبلغ',
        'state': 'الحالة', 'invoice_id': 'الفاتورة',
    },
    'care.contract.pnl': {
        'project_id': 'المشروع', 'partner_id': 'العميل', 'sector': 'القطاع',
        'date_from': 'من تاريخ', 'date_to': 'إلى تاريخ', 'worker_count': 'عدد العمال',
        'revenue': 'الإيراد', 'cost_wages': 'الأجور', 'cost_allowances': 'البدلات',
        'cost_eos': 'مخصص نهاية الخدمة', 'cost_total': 'إجمالي التكلفة',
        'cost_per_worker': 'التكلفة لكل عامل', 'margin': 'الهامش', 'margin_pct': 'نسبة الهامش %',
    },
    'care.expense.claim': {
        'name': 'المرجع', 'employee_id': 'الموظف', 'expense_type': 'نوع المصروف',
        'expense_date': 'التاريخ', 'amount': 'المبلغ', 'receipt': 'الإيصال',
        'has_receipt': 'يوجد إيصال', 'description': 'الوصف', 'reimburse_method': 'طريقة الرد',
        'custody_id': 'العُهدة النقدية', 'reimbursed_date': 'تاريخ الرد', 'state': 'الحالة',
    },
    'care.insurance.policy': {
        'name': 'المرجع', 'employee_id': 'الموظف', 'insurer': 'شركة التأمين',
        'policy_no': 'رقم الوثيقة', 'insurance_type': 'نوع التأمين', 'category': 'الفئة',
        'start_date': 'تاريخ البدء', 'expiry_date': 'تاريخ الانتهاء', 'premium': 'القسط',
        'days_to_expiry': 'أيام حتى الانتهاء', 'state': 'الحالة',
    },
    'care.gosi': {
        'employee_id': 'الموظف', 'registration_no': 'رقم التسجيل',
        'gosi_wage': 'الأجر الخاضع', 'company_rate': 'نسبة الشركة %',
        'employee_rate': 'نسبة الموظف %', 'company_amount': 'حصة الشركة',
        'employee_amount': 'حصة الموظف', 'active': 'نشط',
    },
    'care.exception': {
        'name': 'المشكلة', 'category': 'الفئة', 'severity': 'الخطورة',
        'count': 'العدد', 'impact': 'الأثر', 'state': 'الحالة', 'scan_date': 'تاريخ الفحص',
    },
    'care.attrition': {
        'dimension': 'البُعد', 'dimension_label': 'المجموعة', 'headcount': 'العدد',
        'departures': 'المغادرون', 'rate': 'نسبة التسرّب %',
    },
    'care.attrition.risk': {
        'employee_id': 'الموظف', 'department_id': 'القسم', 'indicators': 'المؤشرات',
        'score': 'الدرجة', 'risk': 'مستوى الخطر',
    },
    'care.hse.incident': {
        'name': 'المرجع', 'date': 'التاريخ', 'employee_id': 'الموظف', 'project_id': 'المشروع',
        'location': 'الموقع', 'incident_type': 'نوع الحادث', 'severity': 'الخطورة',
        'description': 'الوصف', 'root_cause': 'السبب الجذري', 'corrective_action': 'الإجراء التصحيحي',
        'state': 'الحالة',
    },
    'care.equipment': {
        'name': 'رقم الأصل', 'asset_name': 'الأصل', 'category': 'الفئة',
        'employee_id': 'مُسلَّم إلى', 'project_id': 'المشروع', 'issue_date': 'تاريخ الصرف',
        'return_date': 'تاريخ الإرجاع', 'condition': 'الحالة', 'state': 'الوضع',
    },
    'care.workforce.plan': {
        'job_id': 'الوظيفة', 'department_id': 'القسم', 'required_headcount': 'المطلوب',
        'actual_headcount': 'الفعلي', 'gap': 'الفجوة', 'fill_rate': 'نسبة الإشغال',
    },
    # ---- older care models (common fields; unmatched names are skipped) ----
    'care.penalty': {
        'name': 'المرجع', 'employee_id': 'الموظف', 'project_id': 'المشروع', 'penalty_type_id': 'نوع الجزاء',
        'date': 'التاريخ', 'amount': 'المبلغ', 'reason': 'السبب', 'state': 'الحالة', 'note': 'ملاحظات',
    },
    'care.allowance': {
        'name': 'المرجع', 'employee_id': 'الموظف', 'allowance_type_id': 'نوع البدل',
        'date': 'التاريخ', 'amount': 'المبلغ', 'payment_method': 'طريقة الدفع', 'state': 'الحالة',
    },
    'care.traffic.violation': {
        'name': 'المرجع', 'driver_id': 'السائق', 'vehicle_id': 'المركبة', 'violation_type_id': 'نوع المخالفة',
        'plate_no': 'رقم اللوحة', 'date': 'التاريخ', 'amount': 'المبلغ', 'responsible': 'المسؤول',
        'state': 'الحالة',
    },
    'care.custody': {
        'name': 'المرجع', 'employee_id': 'الموظف', 'item_type': 'نوع العُهدة', 'description': 'البند',
        'issue_date': 'تاريخ الصرف', 'return_date': 'تاريخ الإرجاع', 'value': 'القيمة', 'state': 'الحالة',
    },
    'care.grievance': {
        'name': 'المرجع', 'employee_id': 'الموظف', 'category': 'الفئة', 'date': 'التاريخ',
        'description': 'الوصف', 'resolution': 'الحل', 'state': 'الحالة',
    },
    'care.eos': {
        'name': 'المرجع', 'employee_id': 'الموظف', 'join_date': 'تاريخ المباشرة', 'last_day': 'آخر يوم',
        'reason': 'السبب', 'service_years': 'سنوات الخدمة', 'amount': 'المبلغ', 'state': 'الحالة',
    },
    'care.eos.liability': {
        'employee_id': 'الموظف', 'department_id': 'القسم', 'join_date': 'تاريخ المباشرة',
        'service_years': 'سنوات الخدمة', 'basic_wage': 'الأجر الأساسي', 'provision_days': 'أيام المخصص',
        'provision_amount': 'مبلغ المخصص',
    },
    'care.passport': {
        'name': 'المرجع', 'employee_id': 'الموظف', 'passport_no': 'رقم الجواز', 'country_id': 'الدولة',
        'issue_date': 'تاريخ الإصدار', 'expiry_date': 'تاريخ الانتهاء', 'state': 'الحالة', 'location': 'الموقع',
    },
    'care.deployment': {
        'name': 'المرجع', 'employee_id': 'الموظف', 'project_id': 'المشروع', 'site_location': 'الموقع',
        'start_date': 'تاريخ البدء', 'end_date': 'تاريخ الانتهاء', 'state': 'الحالة',
    },
    'care.gov.transaction': {
        'name': 'المرجع', 'employee_id': 'الموظف', 'transaction_type': 'نوع المعاملة', 'date': 'التاريخ',
        'amount': 'المبلغ', 'reference': 'المرجع الحكومي', 'state': 'الحالة',
    },
    'care.site.permit': {
        'name': 'المرجع', 'employee_id': 'الموظف', 'project_id': 'المشروع', 'permit_type': 'نوع التصريح',
        'issue_date': 'تاريخ الإصدار', 'expiry_date': 'تاريخ الانتهاء', 'state': 'الحالة',
    },
    'care.letter': {
        'name': 'المرجع', 'employee_id': 'الموظف', 'letter_type': 'نوع الخطاب', 'date': 'التاريخ',
        'body': 'النص', 'state': 'الحالة',
    },
    'care.movement': {
        'name': 'المرجع', 'employee_id': 'الموظف', 'movement_type': 'نوع الحركة',
        'department_id': 'القسم', 'date': 'التاريخ', 'state': 'الحالة',
    },
    'care.probation': {
        'name': 'المرجع', 'employee_id': 'الموظف', 'start_date': 'تاريخ البدء', 'end_date': 'تاريخ الانتهاء',
        'review_date': 'تاريخ المراجعة', 'state': 'الحالة',
    },
    'care.bonus': {
        'name': 'المرجع', 'employee_id': 'الموظف', 'bonus_type': 'نوع المكافأة', 'date': 'التاريخ',
        'amount': 'المبلغ', 'payment_method': 'طريقة الدفع', 'reason': 'السبب', 'state': 'الحالة',
    },
    'care.worker.quality': {
        'employee_id': 'الموظف', 'project_id': 'المشروع', 'overall': 'التقييم العام', 'tier': 'التصنيف',
    },
    'care.request': {
        'name': 'المرجع', 'employee_id': 'الموظف', 'request_type': 'نوع الطلب', 'date': 'التاريخ',
        'description': 'الوصف', 'state': 'الحالة',
    },
    'care.sla': {
        'name': 'المرجع', 'project_id': 'المشروع', 'contract_id': 'العقد', 'partner_id': 'العميل',
        'date': 'التاريخ', 'required_headcount': 'المطلوب', 'present_count': 'الحاضرون',
        'gap': 'العجز', 'coverage_pct': 'نسبة التغطية %', 'penalty_per_head': 'غرامة كل عامل ناقص',
        'penalty_risk': 'مخاطرة الغرامة', 'state': 'الحالة',
    },
    'hr.department': {
        'suggested_project_id': 'المشروع المقترَح', 'suggested_score': 'نسبة التطابق %',
    },
    'hr.employee': {
        'device_attendance_count': 'عدد بصمات الحضور',
        'device_attendance_ids': 'سجلات الحضور والانصراف',
        'present_days_month': 'أيام حضور هذا الشهر',
    },
    'care.loan': {
        'name': 'المرجع', 'employee_id': 'الموظف', 'loan_type': 'النوع', 'date': 'التاريخ',
        'amount': 'المبلغ', 'installments': 'عدد الأقساط', 'installment_amount': 'القسط الشهري',
        'start_date': 'بداية الخصم', 'paid_amount': 'المدفوع', 'balance': 'المتبقّي',
        'reason': 'السبب', 'state': 'الحالة',
    },
    'hostel': {'occupancy_pct': 'نسبة الإشغال %', 'occupancy_band': 'فئة الإشغال'},
}

# model -> field -> {value: arabic}
SELECTIONS = {
    'care.client.billing': {
        'billing_basis': {'annual_contract': 'عقد سنوي', 'contract': 'عقد', 'work_order': 'أمر عمل'},
        'price_type': {'per_day': 'لكل يوم-عامل', 'fixed': 'ثابت/شهري'},
        'state': {'draft': 'مسودة', 'awaiting_client': 'بانتظار العميل',
                  'approved': 'معتمد من العميل', 'invoiced': 'مفوتر'},
    },
    'care.contract.pnl': {'sector': {'gov': 'حكومي', 'private': 'خاص'}},
    'care.expense.claim': {
        'expense_type': {'transport': 'مواصلات/مهمة', 'tools': 'أدوات/معدات', 'fees': 'رسوم',
                         'medical': 'طبي', 'supplies': 'مستلزمات', 'other': 'أخرى'},
        'reimburse_method': {'in_payslip': 'عبر الراتب', 'cash': 'نقدًا'},
        'state': {'draft': 'مسودة', 'submitted': 'مُقدَّمة', 'mgr_approved': 'اعتماد المدير',
                  'approved': 'اعتماد المالية', 'reimbursed': 'تم الرد', 'refused': 'مرفوضة'},
    },
    'care.insurance.policy': {
        'insurance_type': {'health': 'صحي', 'life': 'حياة', 'accident': 'حوادث', 'other': 'أخرى'},
        'state': {'valid': 'سارية', 'renew_soon': 'تجديد قريب', 'expired': 'منتهية'},
    },
    'care.exception': {
        'category': {'data': 'جودة البيانات', 'compliance': 'الامتثال',
                     'payroll': 'الرواتب', 'operational': 'تشغيلي'},
        'severity': {'info': 'معلومة', 'warning': 'تحذير', 'critical': 'حرج'},
        'state': {'open': 'مفتوح', 'handled': 'مُعالَج'},
    },
    'care.attrition': {'dimension': {'department': 'القسم/المشروع', 'country': 'الجنسية', 'job': 'الوظيفة'}},
    'care.sla': {'state': {'ok': 'مُغطّى', 'warning': 'دون المستهدف', 'breach': 'إخلال'}},
    'care.attrition.risk': {'risk': {'low': 'منخفض', 'medium': 'متوسط', 'high': 'عالٍ'}},
    'hostel': {'occupancy_band': {'low': 'منخفض (<60%)', 'mid': 'متوسط (60-90%)', 'high': 'مرتفع (>90%)'}},
    'care.hse.incident': {
        'incident_type': {'injury': 'إصابة', 'near_miss': 'شبه حادث', 'property': 'أضرار ممتلكات',
                          'violation': 'مخالفة سلامة', 'fire': 'حريق', 'other': 'أخرى'},
        'severity': {'low': 'منخفضة', 'medium': 'متوسطة', 'high': 'عالية', 'critical': 'حرجة'},
        'state': {'reported': 'مُبلَّغ', 'investigating': 'قيد التحقيق', 'closed': 'مغلق'},
    },
    'care.equipment': {
        'category': {'ppe': 'مهمات وقاية', 'tool': 'أداة', 'device': 'جهاز', 'gear': 'عتاد', 'other': 'أخرى'},
        'condition': {'new': 'جديد', 'good': 'جيد', 'damaged': 'تالف', 'lost': 'مفقود'},
        'state': {'assigned': 'مُسلَّم', 'returned': 'مُرجَع', 'retired': 'مُستبعَد'},
    },
}


class CareI18n(models.AbstractModel):
    _name = 'care.i18n'
    _description = 'Care Arabic Translations'

    @api.model
    def _apply_ar(self):
        IrField = self.env['ir.model.fields'].sudo()
        Sel = self.env['ir.model.fields.selection'].sudo()
        # menus
        for xmlid, ar in MENUS.items():
            m = self.env.ref('care_hr.' + xmlid, raise_if_not_found=False)
            if m:
                m.with_context(lang=LANG).write({'name': ar})
        # action names
        for xmlid, ar in ACTIONS.items():
            a = self.env.ref('care_hr.' + xmlid, raise_if_not_found=False)
            if a:
                a.with_context(lang=LANG).write({'name': ar})
        # field labels
        for model, fmap in FIELDS.items():
            recs = IrField.search([('model', '=', model), ('name', 'in', list(fmap))])
            for f in recs:
                f.with_context(lang=LANG).write({'field_description': fmap[f.name]})
        # selection labels
        for model, fields_map in SELECTIONS.items():
            for fname, vmap in fields_map.items():
                sels = Sel.search([('field_id.model', '=', model), ('field_id.name', '=', fname)])
                for s in sels:
                    if s.value in vmap:
                        s.with_context(lang=LANG).write({'name': vmap[s.value]})
        return True
