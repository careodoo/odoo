# -*- coding: utf-8 -*-
{
    'name': 'CARE — Disinfection',
    'summary': 'Disinfection rounds documented by contact time, approved products and ATP swabs',
    'version': '17.0.1.0.0', 'author': 'CARE', 'license': 'LGPL-3',
    'depends': ['care_cafm', 'hr'],
    'data': ['security/ir.model.access.csv', 'data/disinfect_data.xml', 'views/disinfect_views.xml'],
    'installable': True, 'application': True,
}
