from odoo import fields, models, api


class ProposalServiceLocation(models.Model):
    _name = 'proposal.service.location'
    _description = 'Proposal Service Location'

    name = fields.Char(required=True)
