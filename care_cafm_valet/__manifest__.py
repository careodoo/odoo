# -*- coding: utf-8 -*-
{
    'name': 'CARE — خدمة صف السيارات (Valet Parking)',
    'summary': 'خدمة الفاليه: استلام المركبات، بطاقات ترقيم، مواقف، تسليم، ورديات ومحصّلات',
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
