# -*- coding: utf-8 -*-
{
    'name': "Care Stock",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'stock'],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/activity_type.xml',
        'data/sequence.xml',
        'data/server_action.xml',
        'views/product_update_request.xml',
        'views/stock_warehouse.xml',
        'views/stock_scrap.xml',
        'wizards/scrap_report.xml',
        'reports/report_stockpicking_operations.xml',
        'reports/report_deliveryslip.xml',
        'reports/scrap_report.xml',
        'reports/stock_scrap.xml',
    ],
}
