# -*- coding: utf-8 -*-
{
    'name': 'CARE — خدمة الضيافة (Hospitality)',
    'summary': 'طلبات المشروبات والضيافة: أقسام وأصناف بمواصفات، شاشة مطبخ لايف، حدود استهلاك وإحصائيات',
    'version': '17.0.1.0.0',
    'author': 'CARE',
    'license': 'LGPL-3',
    'depends': ['care_cafm', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/hosp_data.xml',
        'data/hosp_demo.xml',
        'views/hosp_views.xml',
    ],
    'installable': True,
    'application': True,
}
