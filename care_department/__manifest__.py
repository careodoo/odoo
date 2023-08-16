# -*- coding: utf-8 -*-
{
    'name': "Care Department",

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
    'depends': [
        'base', 'hr', 'care_sale', 'purchase', 'fleet', 'project', 'hr_attendance', 'hr_recruitment', 'hr_employee_shift',
        'sp_letter_v15', 'hr_holidays',
    ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/hr_department.xml',
        'views/fleet_vehicle.xml',
    ],
}
