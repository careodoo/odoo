from odoo import api, fields, models, tools


class TenderCompetitor(models.Model):
    """Aggregated, read-only profile per competitor, built from the tender bid lines.

    One row per (competitor partner, company). All raw counters come from the SQL
    view; rates/score are computed on the fly.
    """
    _name = 'purchase.tender.competitor'
    _description = 'Competitor Analysis'
    _auto = False
    _order = 'threat_score desc, wins desc'

    partner_id = fields.Many2one('res.partner', string='المنافس', readonly=True)
    group_id = fields.Many2one('res.partner', string='المالك / المجموعة', readonly=True)
    is_watched = fields.Boolean(string='مُتابَع', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    total_bids = fields.Integer(string='عدد العطاءات', readonly=True)
    wins = fields.Integer(string='مرات الفوز', readonly=True)
    win_rate = fields.Float(string='معدل الفوز %', readonly=True)
    ministries = fields.Integer(string='عدد الجهات', readonly=True)
    avg_price = fields.Float(string='متوسط السعر', readonly=True, group_operator='avg')
    avg_gap = fields.Float(string='متوسط الفارق عن الفائز', readonly=True, group_operator='avg')
    avg_rank = fields.Float(string='متوسط الترتيب', readonly=True, group_operator='avg')
    price_index = fields.Float(string='مؤشر السعر %', readonly=True, group_operator='avg',
                               help="Their average price as % of the winning price (>100 = pricier than the winner, <100 = cheaper).")
    last_seen = fields.Date(string='آخر ظهور', readonly=True)
    first_seen = fields.Date(string='أول ظهور', readonly=True)
    is_new_entrant = fields.Boolean(string='منافس جديد (٩٠ يوم)', readonly=True)
    top_ministry_id = fields.Many2one('res.partner', string='الجهة الأكثر استهدافاً', readonly=True)

    # head-to-head vs us
    tenders_vs_us = fields.Integer(string='مواجهات معنا', readonly=True)
    we_beat_them = fields.Integer(string='تغلّبنا عليه', readonly=True)
    they_beat_us = fields.Integer(string='تغلّب علينا', readonly=True)
    our_win_rate_vs = fields.Float(string='معدل فوزنا ضده %', readonly=True)
    threat_score = fields.Float(string='مؤشر الخطورة', readonly=True,
                                help="Higher = more dangerous: blends their win-rate, how often they beat us, and their activity.")

    def init(self):
        cr = self.env.cr
        # Ordering safety: on -u this view may be (re)built before res.partner gets
        # its new columns. Ensure they exist first (idempotent); Odoo reconciles later.
        cr.execute("ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS tender_group_id integer")
        cr.execute("ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS tender_is_competitor boolean")
        cp = self.env['ir.config_parameter'].sudo()
        new_days = int(cp.get_param('purchase_tender.new_entrant_days', 90) or 90)
        w_beat = float(cp.get_param('purchase_tender.threat_beat', 5) or 5)
        w_win = float(cp.get_param('purchase_tender.threat_win', 2) or 2)
        w_bid = float(cp.get_param('purchase_tender.threat_bid', 0.3) or 0.3)
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""
            CREATE VIEW %s AS (
                WITH our_bids AS (
                    SELECT tender_id, min(rank) FILTER (WHERE rank > 0) AS our_rank
                    FROM purchase_tender_price_analysis
                    WHERE is_ours = true
                    GROUP BY tender_id
                ),
                agg AS (
                    SELECT
                        c.contact                                                AS partner_id,
                        c.company_id                                             AS company_id,
                        count(*)                                                 AS total_bids,
                        count(*) FILTER (WHERE c.is_winner)                      AS wins,
                        count(DISTINCT c.organization)                           AS ministries,
                        avg(c.price)                                             AS avg_price,
                        avg(c.gap_vs_winner)                                     AS avg_gap,
                        round((avg(c.rank) FILTER (WHERE c.rank > 0))::numeric, 1)  AS avg_rank,
                        round((avg(c.price / nullif(c.winner_price, 0) * 100)
                               FILTER (WHERE c.price > 0 AND c.winner_price > 0))::numeric, 1) AS price_index,
                        max(c.issue_date)                                        AS last_seen,
                        min(c.issue_date)                                        AS first_seen,
                        mode() WITHIN GROUP (ORDER BY c.organization)            AS top_ministry_id,
                        count(DISTINCT c.tender_id) FILTER (WHERE ob.tender_id IS NOT NULL)                           AS tenders_vs_us,
                        count(DISTINCT c.tender_id) FILTER (WHERE ob.our_rank IS NOT NULL AND c.rank > 0 AND ob.our_rank < c.rank) AS we_beat_them,
                        count(DISTINCT c.tender_id) FILTER (WHERE ob.our_rank IS NOT NULL AND c.rank > 0 AND c.rank < ob.our_rank) AS they_beat_us
                    FROM purchase_tender_price_analysis c
                    LEFT JOIN our_bids ob ON ob.tender_id = c.tender_id
                    WHERE c.is_ours = false AND c.contact IS NOT NULL
                    GROUP BY c.contact, c.company_id
                )
                SELECT
                    row_number() OVER ()       AS id,
                    agg.*,
                    coalesce(pp.tender_group_id, agg.partner_id)  AS group_id,
                    coalesce(pp.tender_is_competitor, false)      AS is_watched,
                    (agg.first_seen >= CURRENT_DATE - interval '%s days')  AS is_new_entrant,
                    CASE WHEN total_bids > 0 THEN round((wins::numeric / total_bids) * 100, 1) ELSE 0 END           AS win_rate,
                    CASE WHEN tenders_vs_us > 0 THEN round((we_beat_them::numeric / tenders_vs_us) * 100, 1) ELSE 0 END AS our_win_rate_vs,
                    round(they_beat_us * %s + wins * %s + total_bids * %s, 1)  AS threat_score
                FROM agg
                LEFT JOIN res_partner pp ON pp.id = agg.partner_id
            )
        """ % (self._table, new_days, w_beat, w_win, w_bid))

    def action_view_bids(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.partner_id.name,
            'res_model': 'purchase.tender.price.analysis',
            'view_mode': 'tree,pivot,graph',
            'domain': [('contact', '=', self.partner_id.id), ('is_ours', '=', False)],
            'context': {'search_default_g_org': 1},
        }
