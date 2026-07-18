# -*- coding: utf-8 -*-
{
    'name': "Care CAFM — Maintenance",
    'summary': "Professional maintenance management: departments & trades, spare "
               "parts store, fault/breakdown reports (→ work orders), and periodic "
               "inspection schedules with checklists.",
    'author': "care-kw",
    'category': 'Services/Facility Management',
    'version': '17.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['care_cafm', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/maint_data.xml',
        'views/maintenance_views.xml',
    ],
    'installable': True,
    'application': False,
}
