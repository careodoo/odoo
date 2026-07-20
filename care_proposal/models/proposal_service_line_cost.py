from odoo import fields, models


class ProposalServiceLineCost(models.Model):
    """Frozen cost-component breakdown captured on a proposal service line.

    This is the SNAPSHOT: once written it is never re-read from the catalog,
    so editing a service/cost-book later can never change an existing proposal.
    Re-syncing is always explicit (a button), never silent."""

    _name = 'proposal.service.line.cost'
    _description = 'Proposal Service Line Cost Snapshot'
    _order = 'sequence, id'

    line_id = fields.Many2one(
        'proposal.service.line', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    component_id = fields.Many2one('proposal.cost.component', string='Component')
    name = fields.Char(string='Label')
    amount = fields.Float(digits=(16, 3), )
    note = fields.Char()
