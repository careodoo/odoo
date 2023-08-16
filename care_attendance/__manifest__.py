# -*- coding: utf-8 -*-
{
    'name': "care_attendance",

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
    'depends': ['base', 'hr', 'hr_attendance', 'report_xlsx'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/sequence.xml',
        'data/cron.xml',
        'data/activity_type.xml',
        'data/mail_templates.xml',
        'views/res_config_settings.xml',
        'views/hr_employee.xml',
        'views/bulk_attendance.xml',
        'views/hr_attendance.xml',
        'reports/care_attendance_xlsx.xml',
        'wizards/attendance_refuse.xml',
        'wizards/attendance_xlsx.xml',
    ],
}
