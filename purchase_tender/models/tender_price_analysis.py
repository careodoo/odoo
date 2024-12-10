from odoo import _, api, fields, models


class TenderPriceAnalysis(models.Model):
    _name = 'purchase.tender.price.analysis'
    _description = 'Purchase Tender Price Analysis'
    _order = 'id desc'

    name = fields.Char(string="Description")
    sequence = fields.Integer(default=10)
    rank = fields.Integer(compute='compute_rank', store=True)
    contact = fields.Many2one('res.partner')
    price = fields.Float()
    rate = fields.Float(compute='compute_rate', store=True)
    tender_id = fields.Many2one('purchase.tender')
    state = fields.Selection(
        selection=[
            ('accepted', 'Accepted'),
            ('excepted', 'Excepted'),
        ],
        string='Status',
        default='accepted',
    )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        default=lambda self: self.env.company,
        required=True,
    )

    @api.depends('tender_id.manpower', 'tender_id.period', 'price')
    def compute_rate(self):
        for rec in self:
            if rec.tender_id.manpower and rec.tender_id.period and rec.price:
                rec.rate = rec.price / rec.tender_id.period / rec.tender_id.manpower
            else:
                rec.rate = 0

    @api.depends('price', 'tender_id.price_analysis_ids', 'state')
    def compute_rank(self):
        for rec in self:
            rec.rank = 0
            if rec.price and rec.tender_id.price_analysis_ids and rec.state != 'excepted':
                prices = rec.tender_id.price_analysis_ids.filtered(
                    lambda p: p.state != 'excepted').mapped('price')
                prices.sort()
                lst = [i for i, x in enumerate(prices) if x == rec.price]
                if len(lst):
                    rec.rank = lst[0] + 1
                    rec.sequence = rec.rank
            else:
                rec.rank = 0
                rec.sequence = 100
