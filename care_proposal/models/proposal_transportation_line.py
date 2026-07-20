from odoo import _, api, fields, models


class ProposalTransportationLine(models.Model):
    _name = 'proposal.transportation.line'
    _description = 'Proposal Transportation Line'

    proposal_id = fields.Many2one('proposal.proposal')
    transportation_id = fields.Many2one(
        'proposal.transportation',
        required=True,
    )
    service_ids = fields.Many2many(
        'proposal.service.line',
        domain="[('proposal_id', '=', proposal_id)]",
        required=True,
    )
    cost = fields.Float(digits=(16, 3), 
        related='transportation_id.cost',
        store=True,
    )
    type = fields.Selection(
        related='transportation_id.type',
        store=True,
    )
    period = fields.Selection(
        related='transportation_id.period',
    )

    @api.onchange('transportation_id')
    def onchange_transportation_id(self):
        return {'domain': {'service_ids': [('id', 'in', self.proposal_id.service_ids.ids)]}}
