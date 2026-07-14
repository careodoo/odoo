# -*- coding: utf-8 -*-
{
    'name': 'Care Reports (Letterhead + Barcode/QR)',
    'summary': 'Unified CARE letterhead reports with barcode + QR, starting with Resignation',
    'category': 'Human Resources',
    'version': '17.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'hr', 'nthub_hr_resignation'],
    'data': [
        'reports/paperformat.xml',
        'reports/resignation_report.xml',
    ],
    'assets': {},
    'installable': True,
    'application': False,
}
