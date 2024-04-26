from odoo import fields, models, api


class ProposalScope(models.Model):
    _name = 'proposal.scope'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Proposal Scope'

    name = fields.Char(required=True)
    schedule = fields.Selection(selection=[
        ('daily', 'Daily'), ('weekly', 'Weekly'),
        ('monthly', 'Monthly'), ('custom', 'As Per Request'), ('other', 'Other'),
    ], required=True)
