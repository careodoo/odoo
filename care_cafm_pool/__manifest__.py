# -*- coding: utf-8 -*-
{
    'name': 'CARE — Pool Maintenance',
    'summary': 'Water chemistry readings with a safe band that closes the pool automatically, plus a maintenance log',
    'version': '17.0.1.0.0',
    'author': 'CARE',
    'license': 'LGPL-3',
    'depends': ['care_cafm', 'hr'],
    'data': ['security/ir.model.access.csv', 'data/pool_data.xml', 'views/pool_views.xml'],
    'installable': True,
    'application': True,
}
