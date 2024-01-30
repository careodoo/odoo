# -*- coding: utf-8 -*-
# Copyright (C) 2021-2022 Artem Shurshilov <shurshilov.a@yandex.ru>
# License OPL-1.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "hr attendance face recognition pro",

    'summary': """
Face recognition check in / out
is a technology capable of identifying or verifying a person
from a digital image or a video frame from a video source""",

    'author': "EURO ODOO, Shurshilov Artem",
    'website': "https://eurodoo.com",
    # "live_test_url": "https://eurodoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '15.7.2.8',
    "license": "OPL-1",
    'price': 122,
    'currency': 'EUR',
    'images': [
        'static/description/preview.gif',
        'static/description/face_control.png',
        'static/description/face_control.png',
        'static/description/face_control.png',
    ],

    # any module necessary for this one to work correctly
    'depends': ['base', 'web', 'hr_attendance_base', 'web_image_webcam', 'field_image_editor'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/res_users.xml',
        'views/hr_employee.xml',
        'views/res_config_settings_views.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'hr_attendance_face_recognition_pro/static/src/css/toogle_button.css',
            'hr_attendance_face_recognition_pro/static/src/js/lib/webcam.js',
            # 'https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@3.12.0/dist/tf.min.js',
            # 'https://cdnjs.cloudflare.com/ajax/libs/human/2.6.1/human.js',
            'hr_attendance_face_recognition_pro/static/src/js/lib/human.js',
            # 'hr_attendance_face_recognition_pro/static/src/js/lib/human.js',
            'hr_attendance_face_recognition_pro/static/src/js/widget_image_recognition.js',
            'hr_attendance_face_recognition_pro/static/src/js/res_users_kanban_face_recognition.js',
            'hr_attendance_face_recognition_pro/static/src/js/my_attendances_face_recognition.js',
            'hr_attendance_face_recognition_pro/static/src/js/kiosk_mode_face_recognition.js',

        ],
        'web.assets_qweb': [
            'hr_attendance_face_recognition_pro/static/src/xml/attendance.xml',
            'hr_attendance_face_recognition_pro/static/src/xml/kiosk.xml',
        ],
    },

    "cloc_exclude": [
        "static/src/js/lib/**/*",  # exclude a single folder
    ]
}
