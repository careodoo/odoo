# -*- coding: utf-8 -*-
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#    LeafByte(2022)
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
{
    'name': 'Sales Report',
    'version': '17.0.0.0',
    'category': 'Sales',
    'summary': """Sales Report of all sales records.""",
    'description': """
        Module Description:
            This module will show all sales records made from the system.
    """,
    'author': 'LeafByte',
    'website': "",
    'company': 'LeafByte',
    'depends': ['base', 'sale', 'point_of_sale'],
    'data': [        
        'security/ir.model.access.csv',
        'views/sales_report_view.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}