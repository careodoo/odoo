# -*- coding: utf-8 -*-
{
    'name': 'CARE — Fuel (Cards & Cash)',
    'summary': 'تسجيل الوقود عبر كروت التعبئة المسبقة أو العهدة النقدية مع إيصال لكل عملية',
    'version': '17.0.1.0.0',
    'author': 'CARE',
    'website': 'https://care-kw.com',
    'license': 'LGPL-3',
    'category': 'Fleet',
    'depends': ['care_pms', 'fleet', 'hr', 'mail'],
    'data': [
        'security/fuel_groups.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'reports/fuel_report.xml',
        'views/fuel_card_views.xml',
        'views/fuel_entry_views.xml',
        'views/fuel_menus.xml',
    ],
    'demo': ['data/demo.xml'],
    'application': True,
    'installable': True,
}
