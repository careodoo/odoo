from odoo import fields, models, api


class ProposalApprover(models.Model):
    _name = 'proposal.approver'
    _description = 'Proposal Approver'
    _order = 'sequence'

    sequence = fields.Integer(default=10)
    user_id = fields.Many2one('res.users', required=True)
