# -*- coding: utf-8 -*-
"""Per-client, per-service preferences — surfaced in the app's More → service
settings. Each client (organisation) tunes how each service behaves for them:
which notifications they receive, and whether they get a weekly digest."""
from odoo import api, fields, models


class ClientServicePref(models.Model):
    _name = 'care.cafm.client.service.pref'
    _description = 'تفضيلات العميل حسب الخدمة'
    _order = 'service_code'

    partner_id = fields.Many2one('res.partner', string='العميل', required=True,
                                 index=True, ondelete='cascade')
    service_code = fields.Char(string='رمز الخدمة', required=True, index=True)

    # notifications the client wants for THIS service
    notify_new = fields.Boolean(string='إشعار عند عمل جديد', default=True)
    notify_done = fields.Boolean(string='إشعار عند الإنجاز', default=True)
    notify_overdue = fields.Boolean(string='إشعار عند التأخّر', default=True)
    weekly_report = fields.Boolean(string='تقرير أسبوعي', default=False)
    # a soft threshold: alert the client if open items exceed this
    alert_threshold = fields.Integer(string='تنبيه عند تجاوز عدد الأعمال المفتوحة', default=0)

    _sql_constraints = [
        ('partner_service_uniq', 'unique(partner_id, service_code)',
         'يوجد إعداد واحد فقط لكل خدمة لكل عميل.'),
    ]

    @api.model
    def get_for(self, partner, codes):
        """Return {code: {prefs}} for a partner, creating defaults lazily so the
        app always gets a full row to toggle."""
        out = {}
        existing = {p.service_code: p for p in self.search([('partner_id', '=', partner.id)])}
        for code in codes:
            p = existing.get(code)
            out[code] = {
                'notify_new': p.notify_new if p else True,
                'notify_done': p.notify_done if p else True,
                'notify_overdue': p.notify_overdue if p else True,
                'weekly_report': p.weekly_report if p else False,
                'alert_threshold': p.alert_threshold if p else 0,
            }
        return out

    @api.model
    def set_for(self, partner, code, vals):
        allowed = {'notify_new', 'notify_done', 'notify_overdue', 'weekly_report', 'alert_threshold'}
        clean = {k: v for k, v in (vals or {}).items() if k in allowed}
        rec = self.search([('partner_id', '=', partner.id), ('service_code', '=', code)], limit=1)
        if rec:
            rec.write(clean)
        else:
            rec = self.create(dict(clean, partner_id=partner.id, service_code=code))
        return rec
