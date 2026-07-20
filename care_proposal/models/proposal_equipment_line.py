from odoo import _, api, fields, models

class ProposalEquipmentLine(models.Model):
    _name = 'proposal.equipment.line'
    _description = 'Proposal Equipment Line'

    proposal_id = fields.Many2one('proposal.proposal')
    product_id = fields.Many2one('product.product', required=True, string='Equipment')
    quantity = fields.Float(default=1)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    cost = fields.Float(digits=(16, 3), required=True)
    total_amount = fields.Float(digits=(16, 3), compute='compute_total_amount', store=True, string='Total')

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.cost = self.product_id.standard_price
            self.uom_id = self.product_id.uom_id.id

    @api.depends('cost', 'quantity')
    def compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.cost * rec.quantity