# -*- coding: utf-8 -*-
{
    'name': "Employee Request for Shifting",

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
    'depends': ['base', 'hr', 'hr_holidays'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'security/rules.xml',
        'data/mail_templates.xml',
        'data/activity.xml',
        'views/employee_shift_request.xml',
        'views/res_config_settings.xml',
        'views/hr_employee.xml',
        'views/hr_department.xml',
        'wizards/request_refuse_reason.xml',
        'reports/shift_report.xml',
        'reports/joining_report.xml',
        'reports/leave_request_report.xml',
    ],
}
