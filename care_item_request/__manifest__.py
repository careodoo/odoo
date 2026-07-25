# -*- coding: utf-8 -*-
{
    'name': 'CARE — Request Items',
    'summary': 'طلب أصناف/مواد من مدير المشروع مع اعتماد وتحويله إلى توريد',
    'version': '17.0.1.0.0',
    'author': 'CARE',
    'website': 'https://care-kw.com',
    'license': 'LGPL-3',
    'category': 'Project',
    'depends': ['care_pms', 'mail'],
    'data': [
        'security/item_request_groups.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'reports/item_request_report.xml',
        'views/item_request_views.xml',
    ],
    'application': True,
    'installable': True,
}
