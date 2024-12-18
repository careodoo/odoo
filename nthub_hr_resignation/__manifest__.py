# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "HR Resignation",
    'version': '15.0',
    'summary': """ HR Resignation """,
    'description': """Manage Employee Resignation""",
    'category': 'Human Resources',
    'author': 'Neoteric Hub',
    'company': 'Neoteric Hub',
    'live_test_url': '',
    'website': 'https://www.neoterichub.com',
    'depends': ['hr', 'account', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'views/hr_employee_resignation_view.xml',
        'views/hr_employee_view.xml',
        'views/menu.xml',
        'views/template/portal_menu.xml',
        'views/template/resignation_template.xml',
        'data/sequence.xml'
    ],
    'demo': [
        # 'demo/demo.xml'
    ],
    'images': ['static/description/banner.gif'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
