{
    'name': "purchase Tender",

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
    'depends': ['base', 'purchase_requisition'],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/rules.xml',
        'data/tender.xml',
        'views/purchase_tender.xml',
        'views/bid_type.xml',
        'views/tender_follower.xml',
        'views/tender_record.xml',
        'reports/tender_bid_result.xml',
        'reports/purchase_tender.xml',


    ],
}
# -*- coding: utf-8 -*-

