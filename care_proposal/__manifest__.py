# -*- coding: utf-8 -*-
{
    'name': "Care Proposal",

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
    'depends': ['base', 'mail', 'product', 'crm', 'report_xlsx', 'report_xlsx_helper'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/activity_type.xml',
        'data/mail_template.xml',
        'views/proposal.xml',
        'views/proposal_service.xml',
        'views/proposal_transportation.xml',
        'views/proposal_manpower.xml',
        'views/proposal_scope.xml',
        'views/proposal_term.xml',
        'views/crm_lead.xml',
        'views/res_config_settings.xml',
        'reports/proposal_report.xml',
        'reports/proposal_sheet_xlsx.xml',
        'reports/proposal_scope_xlsx.xml',
        'reports/proposal_manpower_xlsx.xml',
        'reports/proposal_material_xlsx.xml',
        'reports/proposal_equipment_xlsx.xml',
        'reports/proposal_transportation_xlsx.xml',
        'reports/proposal_term_xlsx.xml',
        'reports/customer_proposal.xml',
    ],
}
