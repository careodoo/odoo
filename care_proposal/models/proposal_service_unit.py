from odoo import fields, models, api


class ProposalServiceUnit(models.Model):
    _name = 'proposal.service.unit'
    _description = 'Proposal Service Unit'

    name = fields.Char(required=True)
