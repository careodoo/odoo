# -*- coding: utf-8 -*-
{
    'name': 'CARE Smart Assistant',
    'version': '17.0.1.0',
    'summary': 'Ask in plain language, get answers from system data (availability, expiry, EOS) — governed by user permissions',
    'author': 'CARE',
    'license': 'LGPL-3',
    'depends': ['care_hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/assistant_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
