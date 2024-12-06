from odoo import _, api, fields, models


class ProposalScopeLine(models.Model):
    _name = 'proposal.scope.line'
    _description = 'Proposal Scope Line'

    proposal_id = fields.Many2one('proposal.proposal')
    proposal_scope_id = fields.Many2one(
        'proposal.scope',
        required=True,
        string='Scope',
    )
    schedule = fields.Selection(
        related='proposal_scope_id.schedule',
    )
