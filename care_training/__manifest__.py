# -*- coding: utf-8 -*-
{
    'name': "Care Training & Certifications",
    'summary': "Internal training courses, sessions, enrollment, results and "
               "certificate-expiry tracking.",
    'author': "care-kw",
    'category': 'Human Resources',
    'version': '17.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['base', 'hr', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/training_views.xml',
    ],
    'application': False,
    'installable': True,
}
