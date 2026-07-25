# -*- coding: utf-8 -*-
{
    'name': 'CARE — Work Suspension Requests',
    'summary': 'طلبات إيقاف العمال عن العمل باعتماد الموارد البشرية + تقرير رسمي',
    'version': '17.0.1.0.0',
    'author': 'CARE',
    'license': 'LGPL-3',
    'depends': ['hr', 'project', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'reports/suspension_report.xml',
        'views/suspension_views.xml',
    ],
    'installable': True,
    'application': False,
}
