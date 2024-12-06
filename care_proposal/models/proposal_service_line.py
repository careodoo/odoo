from odoo import _, api, fields, models


class ProposalServiceLine(models.Model):
    _name = 'proposal.service.line'
    _rec_name = 'proposal_service_id'
    _description = 'Proposal Service Line'

    proposal_id = fields.Many2one('proposal.proposal')
    proposal_service_id = fields.Many2one('proposal.service', required=True, string='Service')
    location_id = fields.Many2one('proposal.service.location')
    unit_id = fields.Many2one('proposal.service.unit')
    daily_hours = fields.Integer(related='proposal_service_id.daily_hours')
    weekly_days = fields.Integer(related='proposal_service_id.weekly_days')
    monthly_days = fields.Integer(related='proposal_service_id.monthly_days')
    quantity = fields.Integer(default=1)
    total_cost = fields.Float(
        related='proposal_service_id.total_cost',
        store=True,
        string='Subtotal',
    )
    total = fields.Float(compute='compute_total', store=True)

    @api.depends('quantity', 'total_cost')
    def compute_total(self):
        for rec in self:
            rec.total = rec.quantity * rec.total_cost

    def get_service_cost(self, type):
        cost = 0
        lines = self.proposal_id.pricing_ids.filtered(lambda p: p.service_id.id == self.id)
        if lines:
            if type == 'material':
                cost = lines[0].material_cost
            elif type == 'equipment':
                cost = lines[0].equipment_cost
            elif type == 'transportation':
                cost = lines[0].transportation_cost
            elif type == 'cost':
                cost = lines[0].cost
            elif type == 'sales':
                cost = lines[0].sales_price
            else:
                cost = lines[0].profit_percentage
        return cost

    def get_commission_amount(self):
        pricing_line = self.proposal_id.pricing_ids.filtered(lambda p: p.service_id.id == self.id)
        return pricing_line.commission_amount if pricing_line else 0
