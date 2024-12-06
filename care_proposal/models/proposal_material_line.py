from odoo import _, api, fields, models


class ProposalMaterialLine(models.Model):
    _name = 'proposal.material.line'
    _description = 'Proposal Material Line'

    proposal_id = fields.Many2one('proposal.proposal')
    product_id = fields.Many2one('product.product', required=True, string='Material')
    quantity = fields.Float(default=1)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    cost = fields.Float(required=True)
    total_amount = fields.Float(compute='compute_total_amount', store=True, string='Total')

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.cost = self.product_id.standard_price
            self.uom_id = self.product_id.uom_id.id

    @api.depends('cost', 'quantity')
    def compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.cost * rec.quantity