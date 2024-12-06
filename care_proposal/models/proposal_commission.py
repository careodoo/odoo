from odoo import _, api, fields, models


class ProposalCommission(models.Model):
    _name = 'proposal.commission.line'
    _description = 'Proposal Commission'

    proposal_id = fields.Many2one('proposal.proposal')
    service_ids = fields.Many2many(
        'proposal.service.line',
        domain="[('proposal_id', '=', proposal_id)]",
        required=True,
    )
    commission = fields.Selection(
        selection=[
            ('ind_cost', 'Individual Cost'),
        ],
        default='ind_cost',
        required=True,
    )
    commission_type = fields.Selection(
        [
            ('percentage', 'Percentage'),
            ('fixed', 'Fixed'),
        ],
        required=True,
    )
    commission_rate = fields.Float()

    @api.onchange('commission')
    def onchange_commission(self):
        return {'domain': {'service_ids': [('id', 'in', self.proposal_id.service_ids.ids)]}}
