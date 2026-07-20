# -*- coding: utf-8 -*-
{
    'name': 'CARE — Hospitality Service (Hospitality)',
    'summary': 'Beverage and hospitality orders: categories and items with specifications, live kitchen display, consumption limits and statistics',
    'version': '17.0.1.0.0',
    'author': 'CARE',
    'license': 'LGPL-3',
    'depends': ['care_cafm', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/hosp_data.xml',
        'data/hosp_stock_data.xml',
        'data/hosp_demo.xml',
        'views/hosp_views.xml',
    ],
    'installable': True,
    'application': True,
}
