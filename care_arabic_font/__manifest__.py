# -*- coding: utf-8 -*-
{
    'name': 'CARE Arabic Font (Tajawal)',
    'version': '17.0.1.0',
    'summary': 'Use the Tajawal font across the Arabic UI (self-hosted)',
    'author': 'CARE',
    'license': 'LGPL-3',
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'care_arabic_font/static/src/css/tajawal.css',
        ],
        'web.assets_frontend': [
            'care_arabic_font/static/src/css/tajawal.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': True,
}
