# -*- coding: utf-8 -*-
{
    'name': 'CARE CAFM — Waste Transfer and Treatment',
    'summary': 'Waste transfer and treatment service within facilities management: orders, trips and reports',
    'version': '17.0.1.0.0',
    'category': 'Services/CAFM',
    'license': 'LGPL-3',
    'author': 'CARE',
    'depends': ['base', 'mail', 'hr', 'portal', 'website', 'care_cafm', 'care_cafm_mobile_api'],
    'data': [
        'security/waste_groups.xml',
        'security/ir.model.access.csv',
        'security/waste_rules.xml',
        'data/waste_sequences.xml',
        'data/waste_service.xml',
        'reports/waste_reports.xml',
        'views/waste_views.xml',
        'views/waste_portal_templates.xml',
        'views/waste_menus.xml',
        'data/waste_migrate_action.xml',
    ],
    'application': True,
    'installable': True,
}
