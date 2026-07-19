# -*- coding: utf-8 -*-
{
    'name': 'CARE — صيانة المسابح (Pool Maintenance)',
    'summary': 'قراءات كيمياء المياه بنطاق آمن يُغلق المسبح تلقائيًا، وسجل أعمال الصيانة',
    'version': '17.0.1.0.0',
    'author': 'CARE',
    'license': 'LGPL-3',
    'depends': ['care_cafm', 'hr'],
    'data': ['security/ir.model.access.csv', 'data/pool_data.xml', 'views/pool_views.xml'],
    'installable': True,
    'application': True,
}
