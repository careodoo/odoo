# -*- coding: utf-8 -*-
{
    'name': "Purchase Limit",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'purchase', 'purchase_report'],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/server_action.xml',
        'data/mail_template_data.xml',
        'views/cost_center.xml',
        'views/purchase_order.xml',
        'views/cost_center_sign.xml',
        'views/purchase_sign.xml',
        'reports/purchase_request.xml',
    ],
}
