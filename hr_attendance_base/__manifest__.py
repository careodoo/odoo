# -*- coding: utf-8 -*-
# Copyright (C) 2019 Artem Shurshilov <shurshilov.a@yandex.ru>
# License OPL-1.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "hr attendance professional policy technical base ",

    'summary': """
        Module provides quick and effective interaction and inheritance
        for all modules dependent on it, forming one eco system""",

    'author': "EURO ODOO, Shurshilov Artem",
    'website': "https://eurodoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '17.0',
    "license": "OPL-1",
    'price': 9,
    'currency': 'EUR',
    'images':[
        'static/description/Attendance_base.png',
        'static/description/Attendance_base.png',
        'static/description/Attendance_base.png',
        'static/description/Attendance_base.png',
    ],

    # any module necessary for this one to work correctly
    'depends': ['base','web','hr_attendance'],

    # always loaded
    'data': [
        'security/hr_attendance_security.xml',
        'views/views.xml',
    ],

    # NOTE: assets intentionally left DISABLED on Odoo 17.
    # The shipped JS (static/src/js/attendances_base.js, kiosk_mode_base.js) is
    # legacy pre-OWL `odoo.define(...)` AMD code that `require('web.core')` and
    # `require('hr_attendance.my_attendances')` / `hr_attendance.kiosk_confirm`.
    # Those AMD modules no longer exist in Odoo 17 (core ships an OWL attendance
    # app), so re-enabling these bundles would break the backend asset build.
    # The `web.assets_qweb` bundle was also removed in Odoo 15+, so that key is
    # invalid here. This module is a base/eco-system layer: the real, v17-ported
    # JS widgets are meant to be provided by the dependent (paid) sibling add-ons
    # (IP/geo/token/webcam/face/kiosk), which are NOT present in this repo.
    # Do not uncomment until the JS is ported to OWL and the sibling modules ship
    # their v17 assets.
    # 'qweb': [
    #     "static/src/xml/base.xml",
    # ],
    # 'assets': {
    #     'web.assets_backend': [
    #         'hr_attendance_base/static/src/css/steps.css',
    #         'hr_attendance_base/static/src/css/sweetalert2.css',
    #         'hr_attendance_base/static/src/js/lib/sweetalert2.js',
    #         'hr_attendance_base/static/src/js/attendances_base.js',
    #         'hr_attendance_base/static/src/js/kiosk_mode_base.js'
    #     ],
    #     'web.assets_qweb': [
    #         'hr_attendance_base/static/src/**/*.xml',
    #     ],
    # },
}
