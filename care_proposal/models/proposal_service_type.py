from odoo import fields, models, api


class ProposalServiceType(models.Model):
    _name = 'proposal.service.type'
    _description = 'Proposal Service Type'

    name = fields.Char(required=True)
