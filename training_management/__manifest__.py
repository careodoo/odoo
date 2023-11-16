# -*- coding: utf-8 -*-
{
    'name': "Training Management",

    'summary': """
        Training Management""",

    'description': """
        Training Management
    """,

    'author': "Ahmed Gaber",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'project', 'website_slides', 'mail', 'website'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/application_stage.xml',
        'data/training_stage.xml',
        'views/training_application.xml',
        'views/training_application_line.xml',
        'views/project_task.xml',
        'views/application_stage.xml',
        'views/training_stage.xml',
        'views/training_center.xml',
        'views/training_room.xml',
        'views/slide_slide.xml',
        'views/slide_channel.xml',
        'reports/training_application.xml',
        'reports/training_application_line.xml',
    ],
}
