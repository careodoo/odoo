# -*- coding: utf-8 -*-
{
    'name': "Care Assets",

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
    'depends': ['base', 'account_asset', 'purchase', 'hr', 'purchase_limit', 'report_xlsx'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/data_mail_template.xml',
        'views/account_asset.xml',
        'views/account_asset_category.xml',
        'views/asset_transfer_approver.xml',
        'views/asset_transfer.xml',
        'reports/asset_report.xml',
        'reports/asset_list.xml',
        'reports/asset_list_xlsx.xml',
        'reports/asset_label.xml',
        'wizards/account_asset_report.xml',
    ],
}
