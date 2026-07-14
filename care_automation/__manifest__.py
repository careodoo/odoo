# -*- coding: utf-8 -*-
{
    'name': 'CARE HR Automation & Approvals',
    'version': '17.0.1.0',
    'summary': 'No-code automation rules, smart approval routing, integration center',
    'author': 'CARE',
    'license': 'LGPL-3',
    'depends': ['care_hr'],
    'data': [
        'security/ir.model.access.csv',
        'security/delegation_security.xml',
        'data/automation_data.xml',
        'views/automation_views.xml',
        'views/approval_views.xml',
        'views/integration_views.xml',
        'views/delegation_views.xml',
        'views/automation_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
