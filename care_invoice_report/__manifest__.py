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
        'security/ir.model.access.csv',
        'wizard/print_type_wizard_view.xml',
        'views/account_move.xml',
        'views/product_template.xml',
        'views/pricelist.xml',
        'reports/report.xml',
    ],
}
