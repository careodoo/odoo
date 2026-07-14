# -*- coding: utf-8 -*-
{
    'name': 'CARE Document Management (DMS)',
    'version': '17.0.1.0',
    'summary': 'Central document repository: classification, retention, versioning, legal hold, disposal',
    'author': 'CARE',
    'license': 'LGPL-3',
    'depends': ['care_hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/dms_data.xml',
        'views/dms_category_views.xml',
        'views/dms_document_views.xml',
        'views/dms_dashboard_views.xml',
        'views/dms_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
