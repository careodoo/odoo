from odoo import fields, models, api


class SaleOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    qoh_available = fields.Float(string="On Hand", compute='_compute_po_qoh')
    foh_available = fields.Float(string="Forecasted")

    @api.depends('product_id')
    def _compute_po_qoh(self):
        for rec in self:
            rec.qoh_available = rec.product_id.qty_available
            rec.foh_available = rec.product_id.virtual_available
