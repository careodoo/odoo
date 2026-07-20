# -*- coding: utf-8 -*-
{
    'name': 'CARE — Material Handling',
    'summary': 'Move requests, crews, equipment and proof-of-delivery for '
               'in-facility material handling',
    'version': '17.0.1.0.0', 'author': 'CARE', 'license': 'LGPL-3',
    'depends': ['care_cafm', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/handling_data.xml',
        'views/handling_views.xml',
    ],
    'installable': True, 'application': True,
}
