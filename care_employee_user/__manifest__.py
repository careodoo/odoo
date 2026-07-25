# -*- coding: utf-8 -*-
{
    'name': 'CARE — Employee ↔ User Link',
    'summary': 'ربط العامل بمستخدم بورتال/داخلي/عام + علامة مستخدم إدارة المشاريع',
    'version': '17.0.1.0.0',
    'author': 'CARE',
    'license': 'LGPL-3',
    'category': 'Human Resources',
    'depends': ['hr', 'project'],
    'data': [
        'views/hr_employee_views.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
}
