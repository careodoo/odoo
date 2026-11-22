# -*- coding: utf-8 -*-
{
    'name': 'CARE — الشكاوى والإجراءات التأديبية',
    'version': '17.0.1.0.0',
    'summary': 'شكاوى ضد الموظفين بمسار اعتماد قانوني (المدير ← HR ← القانونية ← تطبيق الجزاء)',
    'author': 'CARE Group',
    'category': 'Human Resources',
    'depends': [
        'hr', 'mail', 'care_hr', 'care_esignature',
        'care_penalty_bonus', 'care_suspension', 'care_labor_law',
    ],
    'data': [
        'security/discipline_security.xml',
        'security/ir.model.access.csv',
        'data/discipline_data.xml',
        'views/complaint_views.xml',
        'views/res_config_settings_views.xml',
        'views/hr_employee_views.xml',
        'views/menu.xml',
        'reports/complaint_report.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
