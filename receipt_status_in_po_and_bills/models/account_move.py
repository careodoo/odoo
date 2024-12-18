# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class AccountMove(models.Model):
    _inherit = 'account.move'
    receipt_status = fields.Selection(selection=[
        ('nothing', 'Nothing to Receipt'), ('to_receipt', 'To Receipt'),
        ('partial', 'Partially Receipted'), ('receipted', 'Receipted'),
        ('processing', 'Processing')
    ], string='Receipt Status', compute='_compute_receipt_status', store=True,
        readonly=True, copy=False, default='nothing')

    @api.depends('invoice_line_ids.purchase_order_id.receipt_status')
    def _compute_receipt_status(self):
        for rec in self:
            rec.receipt_status = 'nothing'
            purchase_order_id = rec.mapped('invoice_line_ids.purchase_order_id')

            if purchase_order_id:
                rec.receipt_status=purchase_order_id.receipt_status