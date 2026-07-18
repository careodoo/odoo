# -*- coding: utf-8 -*-
{
    'name': "Care CAFM — Mobile API",
    'summary': "Token-authenticated REST/JSON API for the native mobile app "
               "(Flutter, published to Google Play / App Store). Bearer-token auth, "
               "role/service-aware endpoints for CAFM + Security.",
    'author': "care-kw",
    'category': 'Services/Facility Management',
    'version': '17.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['care_cafm', 'care_cafm_security'],
    'data': [
        'security/ir.model.access.csv',
        'security/mobile_rules.xml',
        'data/ir_cron.xml',
        'views/app_center_views.xml',
        'views/notification_views.xml',
        'views/account_deletion_views.xml',
        'reports/orders_report.xml',
    ],
    'installable': True,
    'application': True,  # it has its own control centre now
}
