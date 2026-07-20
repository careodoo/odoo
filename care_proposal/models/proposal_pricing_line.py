from odoo import _, api, fields, models


class ProposalPricingLine(models.Model):
    _name = 'proposal.pricing.line'
    _description = 'Proposal Pricing Line'

    # ondelete='cascade' is what makes (5, 0, 0) DELETE these lines rather
    # than merely null their link. Without it every 'Generate pricing'
    # left the previous lines behind as orphans — 1263 of them had
    # accumulated, 1211 still carrying prices, and because an orphan
    # reads its guard threshold from a proposal that is not there, the
    # below-cost guard could never fire on one.
    proposal_id = fields.Many2one('proposal.proposal', ondelete='cascade',
                                  index=True)
    service_id = fields.Many2one('proposal.service.line')
    service_total_cost = fields.Float(digits=(16, 3), string='S. Total Cost')
    service_individual_cost = fields.Float(digits=(16, 3), string='S. Ind. Cost')
    service_quantity = fields.Float(string='S. Qty')
    material_cost = fields.Float(digits=(16, 3), string='Material')
    equipment_cost = fields.Float(digits=(16, 3), string='Equipment')
    transportation_cost = fields.Float(digits=(16, 3), string='Trans.')
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
    individual_profit_amount = fields.Float(digits=(16, 3), 
        string='Ind. Profit',
        compute='compute_profit',
        store=True,
    )
    profit_amount = fields.Float(digits=(16, 3), string='Total Profit', compute='compute_profit', store=True)
    commission_amount = fields.Float(digits=(16, 3), string='Commission')
    individual_cost = fields.Float(digits=(16, 3), required=True, string='Ind. Cost')
    individual_cost_after_commission = fields.Float(digits=(16, 3), 
        string='Ind. Cost+CO.',
        compute='compute_individual_cost_after_commission',
        store=True,
    )
    cost = fields.Float(digits=(16, 3), required=True)
    individual_sales_price = fields.Float(digits=(16, 3), string='Ind. Sales')
    sales_price = fields.Float(digits=(16, 3), 
        compute='compute_sales_price',
        store=True,
        string='Sales',
    )
    below_guard = fields.Boolean(
        string='Below guard', compute='_compute_below_guard', store=True,
        help="Profit % is below the proposal's margin guard threshold.")

    margin_percentage = fields.Float(
        digits=(16, 3), string='Margin on price %',
        compute='compute_profit', store=True,
        help='Profit as a share of the SELLING price. The guard, the pricing '
             'strategy and the header KPI all speak this language; '
             'profit_percentage is markup on cost and is a different number.')

    @api.depends('individual_sales_price', 'individual_cost_after_commission',
                 'proposal_id.margin_guard_pct')
    def _compute_below_guard(self):
        for rec in self:
            guard = rec.proposal_id.margin_guard_pct or 0.0
            price = rec.individual_sales_price or 0.0
            margin = ((price - (rec.individual_cost_after_commission or 0.0))
                      / price * 100) if price else 0.0
            # Compare like with like. profit_percentage is markup on COST;
            # margin_guard_pct is a margin on PRICE. A line at cost 100 priced
            # at 110 shows 10% markup and passes a 10% guard, while its real
            # margin is 9.09% — under policy, waved through.
            rec.below_guard = bool(price) and margin < guard

    @api.depends('commission_amount', 'individual_cost')
    def compute_individual_cost_after_commission(self):
        for rec in self:
            rec.individual_cost_after_commission = rec.individual_cost + rec.commission_amount

    @api.depends('individual_sales_price', 'individual_cost', 'service_quantity',
                 'commission_amount', 'individual_cost_after_commission')
    def compute_profit(self):
        for rec in self:
            # Always assign first. Without this, clearing a price leaves the
            # previous profit standing — the line still reports a margin it no
            # longer has, and below_guard skips it because the price is empty.
            rec.profit_percentage = 0.0
            rec.individual_profit_amount = 0.0
            rec.profit_amount = 0.0
            rec.margin_percentage = 0.0
            # Divide by what is actually the divisor: cost AFTER commission.
            # Guarding on individual_cost let a line whose cost is entirely
            # commission divide by zero.
            if rec.individual_sales_price and rec.individual_cost_after_commission:
                rec.profit_percentage = (
                    (rec.individual_sales_price - rec.individual_cost_after_commission) /
                    rec.individual_cost_after_commission) * 100
                rec.individual_profit_amount = rec.individual_sales_price - rec.individual_cost_after_commission
                rec.profit_amount = rec.individual_profit_amount * rec.service_quantity
                rec.margin_percentage = (
                    rec.individual_profit_amount / rec.individual_sales_price) * 100

    @api.depends('individual_sales_price', 'service_quantity')
    def compute_sales_price(self):
        for rec in self:
            rec.sales_price = rec.individual_sales_price * rec.service_quantity
