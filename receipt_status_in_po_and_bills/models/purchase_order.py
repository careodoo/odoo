# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    receipt_status = fields.Selection(selection=[
        ('nothing', 'Nothing to Receipt'), ('to_receipt', 'To Receipt'),
        ('partial', 'Partially Receipted'), ('receipted', 'Receipted'),
        ('processing', 'Processing')
    ], string='Receipt Status', compute='_compute_receipt_status', store=True,
        readonly=True, copy=False, default='nothing')

    @api.depends('state', 'order_line.qty_received')
    def _compute_receipt_status(self):
        for rec in self:
            pickings = self.env['stock.picking'].search([('purchase_id', '=', rec.id)])
            orderlines = rec.mapped('order_line').filtered(lambda x:x.product_id.type != 'service')
            service_orderlines =  rec.mapped('order_line').filtered(lambda x:x.product_id.type == 'service')
            if not pickings and not service_orderlines:
                rec.receipt_status = 'nothing'
            elif all(o.qty_received == 0 for o in orderlines):
                rec.receipt_status = 'to_receipt'
            elif orderlines.filtered(lambda x: x.qty_received < x.product_uom_qty):
                rec.receipt_status = 'partial'
            elif all(o.qty_received == o.product_uom_qty for o in orderlines):
                rec.receipt_status = 'receipted'
            if any(p.state in ('waiting', 'confirmed') for p in pickings):
                rec.receipt_status = 'processing'
            if not orderlines and service_orderlines and rec.state == 'purchase':
                rec.receipt_status = 'receipted'
