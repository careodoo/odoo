# -*- coding: utf-8 -*-
{
    'name': 'CARE — Project Permits',
    'summary': 'تصاريح المشروع: الأمنية والصحة والأغذية والدفاع المدني مع تنبيهات الانتهاء',
    'version': '17.0.1.0.0',
    'author': 'CARE',
    'website': 'https://care-kw.com',
    'license': 'LGPL-3',
    'category': 'Project',
    'depends': ['care_pms', 'mail'],
    'data': [
        'security/permit_groups.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/cron.xml',
        'reports/permit_report.xml',
        'views/permit_views.xml',
    ],
    'application': True,
    'installable': True,
}
