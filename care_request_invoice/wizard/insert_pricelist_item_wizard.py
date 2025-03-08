from odoo import models, fields, _, api
from odoo.exceptions import ValidationError


class InsertPricelistItemWizard(models.TransientModel):
    _name = 'insert.pricelist.item.wizard'

    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist',
                                   default=lambda self: self.env.context.get('default_pricelist_id'))
    pricelist_items = fields.Many2many('product.pricelist.item', string='Pricelist Items',
                                       compute='_compute_pricelist_items', readonly=False, store=True)

    @api.depends('pricelist_id')
    def _compute_pricelist_items(self):
        self.pricelist_items = self.env['product.pricelist.item'].search([('pricelist_id', '=', self.pricelist_id.id)])

    def action_insert(self):
        invoice_request = self.env['request.invoice'].browse(self.env.context['active_id'])
        lines = invoice_request.request_invoice_id
        for item in self.pricelist_items:
            lines.create({
                'product_id': item.product_tmpl_id.product_variant_id.id,
                'label': item.product_tmpl_id.product_variant_id.name,
                'price': item.fixed_price,
                'quantity': 1,
                'days': item.product_tmpl_id.days_per_month if invoice_request.labor_service else 1,
                'product_uom_id': item.product_tmpl_id.uom_id.id,
                'request_id': self.env.context['active_id']})

        return {'type': 'ir.actions.act_window_close'}
