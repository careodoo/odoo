from odoo import fields, models, api


class ProposalTerm(models.Model):
    _name = 'proposal.term'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Proposal Term'

    name = fields.Char(required=True)
