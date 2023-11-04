# -*- coding: utf-8 -*-
{
    'name': "Exit Interview",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Ahmed Gaber",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'hr'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/resignation_reason.xml',
        'data/exit_interview_question.xml',
        'data/organization_rate.xml',
        'data/supervisor_rate.xml',
        'views/exit_interview.xml',
        'views/resignation_reason.xml',
        'views/organization_rate.xml',
        'views/supervisor_rate.xml',
        'views/exit_interview_question.xml',
        'reports/exit_interview.xml',
    ],
}
