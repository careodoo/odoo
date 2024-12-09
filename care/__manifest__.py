# -*- coding: utf-8 -*-
{
    'name': 'Care Company',

    'version': '17.0',

    'author': 'Mohab Ahmed Hamed',

    'category': 'Tools',

    'description': """Care Company System""",

    'depends': ['base', 'mail', 'fleet', 'hr', 'purchase'],

    'data': [
        'security/groups.xml',
        'security/rules.xml',
        'security/ir.model.access.csv',
        'data/mail_templates.xml',
        'data/ir_cron.xml',
        'views/res_config_settings.xml',
        'views/custody.xml',
        'views/services_checks.xml',
        'views/fleet_vehicle_log_services.xml',
        'views/hostel.xml',
        'views/hostel_floor.xml',
        'views/hostel_flats.xml',
        'views/hostel_room.xml',
        'views/hostel_beds.xml',
        'views/hostel_maintenance.xml',
        'views/social_contracts.xml',
        'views/social_contracts_authorized_persons.xml',
        'views/social_contracts_date_types.xml',
        'views/hr_employee.xml',
        'views/purchase_order.xml',
    ],
}
