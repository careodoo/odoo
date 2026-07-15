# -*- coding: utf-8 -*-
{
    'name': "CARE 2 CARE — Home Services",
    'summary': "On-demand home services (cleaning, carpet & laundry, maintenance) "
               "for homes and companies: catalogue, booking, visit scheduling, payment.",
    'author': "care-kw",
    'category': 'Services/Home Services',
    'version': '17.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'data/demo_data.xml',
        'views/c2c_views.xml',
        'views/c2c_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'care2care/static/src/dashboard/c2c_dashboard.scss',
            'care2care/static/src/dashboard/c2c_dashboard.js',
            'care2care/static/src/dashboard/c2c_dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
}
