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
    'version': '17.0',
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
        'views/face_attendance_kiosk.xml',
    ],

    # Odoo 17 assets. Migrated from the legacy (commented-out) block that
    # referenced the removed `web.assets_qweb` bundle. In v17, OWL templates
    # (.xml) are co-loaded with the backend bundle, so the separate qweb bundle
    # is gone and the templates are listed directly under web.assets_backend.
    #
    # ORDER MATTERS: the external global libraries (webcam.js -> `Webcam`,
    # human.js -> `Human`) are non-module IIFEs that must be evaluated BEFORE
    # the app ES modules that reference those globals. CSS first, then libs,
    # then the app JS, then the QWeb templates.
    'assets': {
        'web.assets_backend': [
            'hr_attendance_face_recognition_pro/static/src/css/toogle_button.css',
            'hr_attendance_face_recognition_pro/static/src/css/lightbox.css',
            # external globals (plain IIFEs, NOT ES modules) -> load first
            'hr_attendance_face_recognition_pro/static/src/js/lib/webcam.js',
            'hr_attendance_face_recognition_pro/static/src/js/lib/human.js',
            # app ES modules (/** @odoo-module **/)
            'hr_attendance_face_recognition_pro/static/src/js/widget_image_recognition.js',
            'hr_attendance_face_recognition_pro/static/src/js/res_users_kanban_face_recognition.js',
            'hr_attendance_face_recognition_pro/static/src/js/my_attendances_face_recognition.js',
            'hr_attendance_face_recognition_pro/static/src/js/kiosk_mode_face_recognition.js',
            # Face Check-in kiosk client action (self-contained v17 OWL)
            'hr_attendance_face_recognition_pro/static/src/css/face_attendance_kiosk.css',
            'hr_attendance_face_recognition_pro/static/src/js/face_attendance_kiosk.js',
            # OWL/QWeb templates
            'hr_attendance_face_recognition_pro/static/src/xml/attendance.xml',
            'hr_attendance_face_recognition_pro/static/src/xml/kiosk.xml',
            'hr_attendance_face_recognition_pro/static/src/xml/face_attendance_kiosk.xml',
        ],
    },

    "cloc_exclude": [
        "static/src/js/lib/**/*",  # exclude a single folder
    ]
}
