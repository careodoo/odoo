from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    proposal_approver_id = fields.Many2one('res.users', config_parameter='care_proposal.proposal_approver_id')
