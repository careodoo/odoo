# -*- coding: utf-8 -*-
{
    'name': 'CARE Worker Kiosk',
    'version': '17.0.1.0',
    'summary': 'Fingerprint self-service kiosk for workers without smartphones (payslip, leave, docs, grievance, announcements)',
    'author': 'CARE',
    'license': 'LGPL-3',
    'depends': ['care_hr', 'to_attendance_device', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'views/kiosk_config_views.xml',
        'views/kiosk_templates.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
