# -*- coding: utf-8 -*-
{
    'name': "Care HR",

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
    'depends': ['base', 'hr', 'hr_holidays', 'hr_skills', 'care', 'purchase_report'],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/hr_action_joining.xml',
        'views/hr_action_clearance.xml',
        'views/hr_action_absence.xml',
        'views/hr_action_leave_return.xml',
        'views/hr_leave.xml',
        'views/hr_skills.xml',
        'views/hr_employee.xml',
        'wizards/hr_employee_suspend.xml',
        'reports/joining_report.xml',
        'reports/clearance_report.xml',
        'reports/absence_report.xml',
        'reports/leave_return_report.xml',
        'reports/leave_request_report.xml',
    ],
    }
