from odoo import _, api, fields, models


class ProposalReceiver(models.Model):
    _name = 'proposal.receiver'
    _description = 'Proposal Receiver'

    user_id = fields.Many2one('res.users', required=True)
