# -*- coding: utf-8 -*-
{
    'name': "Care CAFM — Cleaning",
    'summary': "Cleaning service inside the CAFM platform: demand/frequency "
               "schedules, weighted quality audits that auto-raise corrective "
               "observations, cleaning rounds with scan-in/out, and a cleaning app.",
    'author': "care-kw",
    'category': 'Services/Facility Management',
    'version': '17.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['care_cafm'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/cleaning_views.xml',
        'reports/reports.xml',
        'data/demo_data.xml',
    ],
    'installable': True,
}
