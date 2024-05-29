# -*- coding: utf-8 -*-
{
    'name': "Manpower Requisition",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Ahmed Gaber",
    'website': "http://www.yourcompany.com",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['base', 'mail', 'hr', 'project'],

    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/activity_type.xml',
        'views/manpower_requisition.xml',
        'reports/manpower_requisition.xml',
    ],
}
