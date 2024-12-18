# -*- coding: utf-8 -*-
###############################################################################
#
#   Skylark Business Solutions
#   Copyright (C) 2004-TODAY OpenERP SA (<http://www.openerp.com>)
#   Copyright (C) 2023-TODAY Skylark Business Solutions.
#
#   See LICENSE file for full copyright and licensing details.
#
###############################################################################

{
	'name': "Product Price History",
	'version': '16.0.1',
	'summary': "This module helps to price history of product",
	'description': "This module helps to price history of product",
	'category': 'Sales',
	'author': 'Skylark Business Solutions',
	'company': 'Skylark Business Solutions',
	'website': '',
	'depends': ['sale','purchase'],
	'data': [
		'views/product_view.xml',
	],
	'license': "OPL-1",
	'images': ['static/description/banner.png'],
	'installable': True,
	'application': True,
}
