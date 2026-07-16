# -*- coding: utf-8 -*-
{
    'name': "CARE — Report Letterhead",
    'summary': "The official CARE letterhead (header + footer) for every printed report.",
    'description': """
Makes the CARE letterhead used by the legacy Disposable Report the company-wide
report layout, so EVERY Odoo report (waste, purchases, sales, invoices, HR ...)
prints with the same header and footer instead of the bare default.

Header: CARE logo + 30th-anniversary badge.
Footer: BICSc / ISO 9001 / ISSA memberships + the bilingual Kuwait address.
    """,
    'author': "care-kw",
    'category': 'Technical/Reporting',
    'version': '17.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['web'],
    'data': [
        'views/report_layout.xml',
    ],
    'installable': True,
    'auto_install': True,
}
