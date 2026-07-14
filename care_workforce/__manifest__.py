# -*- coding: utf-8 -*-
{
    'name': "Care Workforce & Compliance",
    'summary': "Roster scheduling, disciplinary actions, HSE incidents, "
               "workforce planning/succession, and recruitment-agency performance.",
    'author': "care-kw",
    'category': 'Human Resources',
    'version': '17.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['base', 'hr', 'mail', 'project'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/roster_views.xml',
        'views/discipline_views.xml',
        'views/workforce_views.xml',
        'views/agency_views.xml',
        'views/menus.xml',
    ],
    'application': False,
    'installable': True,
}
