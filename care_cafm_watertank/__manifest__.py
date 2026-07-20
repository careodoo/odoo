# -*- coding: utf-8 -*-
{
    'name': 'CARE — Water Tank Cleaning',
    'summary': 'A tank register with a documented cleaning cycle, certificate and lab analysis',
    'version': '17.0.1.0.0', 'author': 'CARE', 'license': 'LGPL-3',
    'depends': ['care_cafm', 'hr'],
    'data': ['security/ir.model.access.csv', 'data/tank_data.xml', 'views/tank_views.xml'],
    'installable': True, 'application': True,
}
