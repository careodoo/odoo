from odoo import models, fields, api

class Pricelist(models.Model):
    _inherit = 'product.pricelist'

    proposal_id = fields.Many2one('proposal.proposal', string='Proposal', store=True)
