from odoo import fields, models, api


class ProposalManpower(models.Model):
    _name = 'proposal.manpower'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Proposal Manpower'

    name = fields.Char(required=True)
    nationality = fields.Many2one('res.country', required=True)
    gender = fields.Selection(selection=[
        ('male', 'Male'), ('female', 'Female'),
    ], required=True)
