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

from odoo import models, fields, api , _
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta

class ProductTemplate(models.Model):
	_inherit = 'product.template'

	sale_order_line_ids = fields.Many2many('sale.order.line','rel_product_template_sale_order_line','product_id','sale_order_line_id','Product Sales Price History Line',compute='_compute_price_sale_history')
	purchase_order_line_ids = fields.Many2many('purchase.order.line','rel_product_template_purchase_order_line','product_id','purchase_order_line_id','Product Purchase Price History Line',compute='_compute_price_purchase_history')
	sale_history_time_type = fields.Selection([('last_day','Last Day'),('last_week','Last Week'),('current_month','Current Month'),
												('last_month','Last Month'),('last_3_month',"Last 3 Month's"),('last_6_month',"Last 6 Month's")],default='last_day',string='Sale History Time Duration')	
	purchase_history_time_type = fields.Selection([('last_day','Last Day'),('last_week','Last Week'),('current_month','Current Month'),
												('last_month','Last Month'),('last_3_month',"Last 3 Month's"),('last_6_month',"Last 6 Month's")],default='last_day',string='Purchase History Time Duration')	

	@api.depends('sale_history_time_type')
	def _compute_price_sale_history(self):
		for rec in self:
			domain = [('product_id','=',rec.product_variant_id.id)]
			today_date = datetime.today()
			# last day wise
			if rec.sale_history_time_type == 'last_day':
				last_day = today_date - relativedelta(days=1)
				domain+=[('order_id.date_order','>=',datetime.combine(last_day, time.min)),('order_id.date_order','<=',datetime.combine(last_day, time.max))]
			# last week wise
			if rec.sale_history_time_type == 'last_week':
				last_day = today_date - relativedelta(days=7)
				domain+=[('order_id.date_order','>=',datetime.combine(last_day, time.min)),('order_id.date_order','<=',today_date)]
			# cuurent month wise
			if rec.sale_history_time_type == 'current_month':
				current_month_start_date = today_date.replace(day=1)
				domain+=[('order_id.date_order','>=',datetime.combine(current_month_start_date, time.min)),('order_id.date_order','<=',today_date)]
			# last month wise
			if rec.sale_history_time_type == 'last_month':
				last_month = today_date - relativedelta(months=1)
				domain+=[('order_id.date_order','>=',datetime.combine(last_month, time.min)),('order_id.date_order','<=',today_date)]
			# last 3 month wise
			if rec.sale_history_time_type == 'last_3_month':
				last_3_month = today_date - relativedelta(months=3)
				domain+=[('order_id.date_order','>=',datetime.combine(last_3_month, time.min)),('order_id.date_order','<=',today_date)]
			# last 6 month wise
			if rec.sale_history_time_type == 'last_6_month':
				last_6_month = today_date - relativedelta(months=6)
				domain+=[('order_id.date_order','>=',datetime.combine(last_6_month, time.min)),('order_id.date_order','<=',today_date)]

			sale_line_ids = self.env['sale.order.line'].search(domain)
			if sale_line_ids:
				rec.sale_order_line_ids = [(6,0,sale_line_ids.ids)]
			else:
				rec.sale_order_line_ids = [(6,0,[])]

	@api.depends('purchase_history_time_type')
	def _compute_price_purchase_history(self):
		for rec in self:
			domain = [('product_id','=',rec.product_variant_id.id)]
			today_date = datetime.today()

			# last day wise
			if rec.purchase_history_time_type == 'last_day':
				last_day = today_date - relativedelta(days=1) 
				domain+=[('date_planned','>=',datetime.combine(last_day, time.min)),('date_planned','<=',datetime.combine(last_day, time.max))]
			# last week wise
			if rec.purchase_history_time_type == 'last_week':
				last_day = today_date - relativedelta(days=7)
				domain+=[('date_planned','>=',datetime.combine(last_day, time.min)),('date_planned','<=',today_date)]
			# cuurent month wise
			if rec.purchase_history_time_type == 'current_month':
				current_month_start_date = today_date.replace(day=1)
				domain+=[('date_planned','>=',datetime.combine(current_month_start_date, time.min)),('date_planned','<=',today_date)]
			# last month wise
			if rec.purchase_history_time_type == 'last_month':
				last_month = today_date - relativedelta(months=1)
				domain+=[('date_planned','>=',datetime.combine(last_month, time.min)),('date_planned','<=',today_date)]
			# last 3 month wise
			if rec.purchase_history_time_type == 'last_3_month':
				last_3_month = today_date - relativedelta(months=3)
				domain+=[('date_planned','>=',datetime.combine(last_3_month, time.min)),('date_planned','<=',today_date)]
			# last 6 month wise
			if rec.purchase_history_time_type == 'last_6_month':
				last_6_month = today_date - relativedelta(months=6)
				domain+=[('date_planned','>=',datetime.combine(last_6_month, time.min)),('date_planned','<=',today_date)]

			purchase_line_ids = self.env['purchase.order.line'].search(domain)
			if purchase_line_ids:
				rec.purchase_order_line_ids = [(6,0,purchase_line_ids.ids)]
			else:
				rec.purchase_order_line_ids = [(6,0,[])]