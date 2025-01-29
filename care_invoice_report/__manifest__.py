# -*- coding: utf-8 -*-
{
    'name': "Care Invoice Report",

    'summary': """
        Care Invoice Report""",

    'description': """
        Care Invoice Report
    """,

    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account'],

    # always loaded
    'data': [
        'views/view.xml',
        'reports/report.xml',
    ],
}
