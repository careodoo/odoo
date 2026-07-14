# -*- coding: utf-8 -*-
{
    'name': 'CARE Document Expiry Alerts',
    'version': '17.0.1.0',
    'summary': 'Proactive alerts for expiring residencies, permits, visas',
    'author': 'CARE',
    'license': 'LGPL-3',
    'depends': ['hr', 'care_hr', 'mail'],
    'data': [
        'data/expiry_params.xml',
        'data/expiry_cron.xml',
        'views/expiry_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
