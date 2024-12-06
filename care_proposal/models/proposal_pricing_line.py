from odoo import _, api, fields, models


class ProposalPricingLine(models.Model):
    _name = 'proposal.pricing.line'
    _description = 'Proposal Pricing Line'

    proposal_id = fields.Many2one('proposal.proposal')
    service_id = fields.Many2one('proposal.service.line')
    service_total_cost = fields.Float(string='S. Total Cost')
    service_individual_cost = fields.Float(string='S. Ind. Cost')
    service_quantity = fields.Float(string='S. Qty')
    material_cost = fields.Float(string='Material')
    equipment_cost = fields.Float(string='Equipment')
    transportation_cost = fields.Float(string='Trans.')
    name = fields.Selection(
        selection=[
            ('service', 'Services'),
            ('material', 'Materials'),
            ('equipment', 'Equipments'),
            ('transportation', 'Transportations'),
        ],
        required=True,
    )
    profit_percentage = fields.Float(string='Profit %', compute='compute_profit', store=True)
    individual_profit_amount = fields.Float(
        string='Ind. Profit',
        compute='compute_profit',
        store=True,
    )
    profit_amount = fields.Float(string='Total Profit', compute='compute_profit', store=True)
    commission_amount = fields.Float(string='Commission')
    individual_cost = fields.Float(required=True, string='Ind. Cost')
    individual_cost_after_commission = fields.Float(
        string='Ind. Cost+CO.',
        compute='compute_individual_cost_after_commission',
        store=True,
    )
    cost = fields.Float(required=True)
    individual_sales_price = fields.Float(string='Ind. Sales')
    sales_price = fields.Float(
        compute='compute_sales_price',
        store=True,
        string='Sales',
    )

    @api.depends('commission_amount', 'individual_cost')
    def compute_individual_cost_after_commission(self):
        for rec in self:
            rec.individual_cost_after_commission = rec.individual_cost + rec.commission_amount

    @api.depends('individual_sales_price', 'individual_cost', 'service_quantity')
    def compute_profit(self):
        for rec in self:
            if rec.individual_sales_price and rec.individual_cost:
                rec.profit_percentage = (
                    (rec.individual_sales_price - rec.individual_cost_after_commission) /
                    rec.individual_cost_after_commission) * 100
                rec.individual_profit_amount = rec.individual_sales_price - rec.individual_cost_after_commission
                rec.profit_amount = rec.individual_profit_amount * rec.service_quantity

    @api.depends('individual_sales_price', 'service_quantity')
    def compute_sales_price(self):
        for rec in self:
            rec.sales_price = rec.individual_sales_price * rec.service_quantity
