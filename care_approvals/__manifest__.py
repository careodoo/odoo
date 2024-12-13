# -*- coding: utf-8 -*-
{
    'name': "Care Approvals",

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
    'depends': ['base', 'approvals', 'hr', 'sale', 'purchase', 'care_sale', 'web_m2x_options','care_department'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/approval_category.xml',
        'views/approval_request.xml',
        'views/product_product.xml',
        'views/hr_department.xml',
        'views/sale_order.xml',
        'views/purchase_order.xml',
        'wizards/approval_request_order.xml',
        'reports/approval_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # 'care_approvals/static/src/js/widget.js',
        ],
        'web.assets_qweb': [
            # 'care_approvals/static/src/xml/widget_view.xml',
        ],
    },
}
