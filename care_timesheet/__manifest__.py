# -*- coding: utf-8 -*-
{
    'name': "Care Timesheet",

    'summary': """
        compare employee attendance within time interval and create new attendance records based on it
        """,

    'description': """
        compare employee attendance within time interval and create new attendance records based on it
    """,

    'author': "Ahmed Gaber",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'hr_attendance'],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/rules.xml',
        'data/sequence.xml',
        'views/care_timesheet.xml',
        'views/hr_attendance.xml',
    ],
}
