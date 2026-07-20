# -*- coding: utf-8 -*-
{
    'name': 'CARE — Valet Parking Service',
    'summary': 'Valet service: vehicle check-in, numbered tickets, parking spots, handover, shifts and cash collections',
    'version': '17.0.1.0.0',
    'author': 'CARE',
    'license': 'LGPL-3',
    'depends': ['care_cafm', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/valet_data.xml',
        'views/valet_views.xml',
    ],
    'installable': True,
    'application': True,
}
