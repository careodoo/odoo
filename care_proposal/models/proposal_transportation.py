from odoo import fields, models, api


class ProposalTransportation(models.Model):
    _name = 'proposal.transportation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Proposal Transportation'

    name = fields.Char(required=True)
    cost = fields.Float()
    period = fields.Selection(selection=[
        ('monthly', 'Monthly'), ('daily', 'Daily'),
    ], required=True)
