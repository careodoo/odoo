from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # --- email notifications (enable/disable each) ---
    tender_email_new = fields.Boolean(
        string='بريد: مناقصة جديدة', default=True,
        config_parameter='purchase_tender.email_new')
    tender_email_status = fields.Boolean(
        string='بريد: تغيير الحالة', default=True,
        config_parameter='purchase_tender.email_status')
    tender_email_date = fields.Boolean(
        string='بريد: تغيير الموعد', default=True,
        config_parameter='purchase_tender.email_date')
    tender_email_closing = fields.Boolean(
        string='بريد: تذكير قرب الإغلاق', default=True,
        config_parameter='purchase_tender.email_closing')
    tender_email_guarantee = fields.Boolean(
        string='بريد: انتهاء الضمان', default=True,
        config_parameter='purchase_tender.email_guarantee')
    tender_email_digest = fields.Boolean(
        string='بريد: الملخّص الأسبوعي', default=True,
        config_parameter='purchase_tender.email_digest')
    tender_email_watchlist = fields.Boolean(
        string='بريد: تنبيه منافس مُتابَع', default=True,
        config_parameter='purchase_tender.email_watchlist')
    tender_email_new_entrants = fields.Boolean(
        string='بريد: منافسون جدد', default=True,
        config_parameter='purchase_tender.email_new_entrants')

    # --- thresholds / timings ---
    tender_closing_soon_days = fields.Integer(
        string='تذكير قبل الإغلاق (أيام)', default=3,
        config_parameter='purchase_tender.closing_soon_days')
    tender_guarantee_days = fields.Integer(
        string='تنبيه قبل انتهاء الضمان (أيام)', default=30,
        config_parameter='purchase_tender.guarantee_days')
    tender_new_entrant_days = fields.Integer(
        string='فترة "منافس جديد" (أيام)', default=90,
        config_parameter='purchase_tender.new_entrant_days')

    # --- threat-score weights (applied after a module update) ---
    tender_threat_beat = fields.Float(
        string='وزن "تغلّب علينا"', default=5.0,
        config_parameter='purchase_tender.threat_beat')
    tender_threat_win = fields.Float(
        string='وزن "مرات الفوز"', default=2.0,
        config_parameter='purchase_tender.threat_win')
    tender_threat_bid = fields.Float(
        string='وزن "عدد العطاءات"', default=0.3,
        config_parameter='purchase_tender.threat_bid')

    # --- win-probability mapping (rank -> %) ---
    tender_winprob_rank1 = fields.Integer(
        string='احتمالية الفوز — الترتيب 1', default=85,
        config_parameter='purchase_tender.winprob_rank1')
    tender_winprob_rank2 = fields.Integer(
        string='احتمالية الفوز — الترتيب 2', default=55,
        config_parameter='purchase_tender.winprob_rank2')
    tender_winprob_rank3 = fields.Integer(
        string='احتمالية الفوز — الترتيب 3', default=35,
        config_parameter='purchase_tender.winprob_rank3')
    tender_winprob_other = fields.Integer(
        string='احتمالية الفوز — ترتيب أدنى', default=20,
        config_parameter='purchase_tender.winprob_other')
    tender_winprob_norank = fields.Integer(
        string='احتمالية الفوز — بدون ترتيب', default=50,
        config_parameter='purchase_tender.winprob_norank')

    # --- defaults ---
    tender_default_checklist = fields.Char(
        string='قائمة التحضير الافتراضية (سطر لكل مهمة)',
        config_parameter='purchase_tender.default_checklist')
    tender_default_view = fields.Selection(
        [('tree', 'قائمة'), ('kanban', 'بطاقات')],
        string='العرض الافتراضي', default='tree',
        config_parameter='purchase_tender.default_view')
    tender_page_size = fields.Integer(
        string='عدد السجلات في الصفحة', default=10,
        config_parameter='purchase_tender.page_size')

    # --- importance (default-sort) tuning ---
    tender_imp_urgent3 = fields.Integer(
        string='حافز إغلاق ≤ 3 أيام', default=400,
        config_parameter='purchase_tender.imp_urgent3')
    tender_imp_urgent7 = fields.Integer(
        string='حافز إغلاق ≤ 7 أيام', default=250,
        config_parameter='purchase_tender.imp_urgent7')
    tender_imp_urgent14 = fields.Integer(
        string='حافز إغلاق ≤ 14 يوم', default=120,
        config_parameter='purchase_tender.imp_urgent14')
    tender_importance_weights = fields.Char(
        string='أوزان الأهمية حسب الحالة',
        config_parameter='purchase_tender.importance_weights')

    # --- AI document analysis ---
    tender_ai_api_key = fields.Char(
        string='مفتاح الذكاء الاصطناعي (Claude)',
        config_parameter='purchase_tender.ai_api_key')

    def set_values(self):
        super().set_values()
        action = self.env.ref('purchase_tender.purchase_tender_action', raise_if_not_found=False)
        if action:
            view = self.tender_default_view or 'tree'
            modes = ['tree', 'kanban', 'form'] if view == 'tree' else ['kanban', 'tree', 'form']
            action.sudo().write({
                'view_mode': ','.join(modes),
                'limit': self.tender_page_size or 10,
            })
        # re-apply settings-driven computed fields so changes take effect at once
        tenders = self.env['purchase.tender'].sudo().search([])
        tenders._compute_win_probability()
        tenders._compute_guarantee_status()
        tenders._compute_importance()

