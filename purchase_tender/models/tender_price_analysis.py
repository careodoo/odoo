from odoo import _, api, fields, models

from .purchase_tender import ACTIVE_STATES


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
            ('accepted', 'مقبول'),
            ('excepted', 'مستبعد'),
        ],
        string='الحالة',
        default='accepted',
    )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        default=lambda self: self.env.company,
        required=True,
    )

    # --- competitor-analysis dimensions (related to the parent tender) ---
    organization = fields.Many2one(related='tender_id.organization', store=True, string='الجهة')
    bid_type = fields.Many2one(related='tender_id.bid_type', store=True, string='النشاط')
    issue_date = fields.Date(related='tender_id.issue_date', store=True, string='تاريخ الإصدار')
    tender_state = fields.Selection(related='tender_id.state', store=True, string='حالة المناقصة')
    winner_price = fields.Float(related='tender_id.winner_price', store=True, string='سعر الفائز')
    is_ours = fields.Boolean(string='عرضنا', compute='_compute_flags', store=True)
    is_winner = fields.Boolean(string='فائز', compute='_compute_flags', store=True)
    win_count = fields.Integer(string='مرات الفوز', compute='_compute_flags', store=True,
                               group_operator='sum')
    gap_vs_winner = fields.Float(string='الفارق عن الفائز', compute='_compute_flags', store=True,
                                 help="This bid's price minus the winning price.")

    @api.depends('contact', 'company_id', 'rank', 'state', 'price', 'tender_id.winner_price')
    def _compute_flags(self):
        for rec in self:
            partner = rec.company_id.partner_id
            won = rec.rank == 1 and rec.state == 'accepted'
            rec.is_ours = bool(rec.contact and partner and rec.contact.id == partner.id)
            rec.is_winner = won
            rec.win_count = 1 if won else 0
            rec.gap_vs_winner = (rec.price - rec.tender_id.winner_price) if (rec.price and rec.tender_id.winner_price) else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            contact = line.contact
            if (contact and contact.tender_is_competitor and line.price
                    and line.tender_id and line.tender_id.state in ACTIVE_STATES):
                line.tender_id.sudo()._send_watchlist_alert(contact)
        return lines

    @api.depends('tender_id.manpower', 'tender_id.period', 'price')
    def compute_rate(self):
        for rec in self:
            if rec.tender_id.manpower and rec.tender_id.period and rec.price:
                rec.rate = rec.price / rec.tender_id.period / rec.tender_id.manpower
            else:
                rec.rate = 0

    @api.depends('price', 'tender_id.price_analysis_ids.price',
                 'tender_id.price_analysis_ids.state', 'state')
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
