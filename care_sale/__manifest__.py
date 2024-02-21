# -*- coding: utf-8 -*-
{
    'name': "Care Sale",

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
    'depends': ['base', 'sale', 'hr', 'purchase_limit', 'eg_sale_line_qoh'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/rules.xml',
        'data/mail_template_data.xml',
        'views/sale_order.xml',
        'views/default_sale_sign_employee.xml',
        'views/sale_sign.xml',
        'views/cost_center.xml',
        'reports/paperformat.xml',
        'reports/layout.xml',
        'reports/sale_order_header.xml',
        'reports/sale_order.xml',
    ],
}
