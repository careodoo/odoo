# -*- coding: utf-8 -*-
"""تقرير النشاط اليومي (Daily Activity Report / DAR) — معيار مهني: ملخّص نهاية
وردية الحارس، يُجمّع نشاط اليوم (دوريات/بلاغات/مهام) تلقائياً + سرد الحارس."""
from odoo import models, fields, api


class SecurityDailyReport(models.Model):
    _name = 'care.security.dar'
    _description = 'تقرير النشاط اليومي'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread']

    name = fields.Char(string='المرجع', default='/', readonly=True, copy=False)
    guard_user_id = fields.Many2one('res.users', string='الحارس', tracking=True,
                                    default=lambda s: s.env.user)
    premise_id = fields.Many2one('security.premise', string='الموقع', tracking=True, index=True)
    date = fields.Date(string='التاريخ', default=fields.Date.context_today, index=True)
    patrols_count = fields.Integer(string='دوريات مُنجَزة')
    incidents_count = fields.Integer(string='بلاغات')
    tasks_count = fields.Integer(string='مهام مُنجَزة')
    visitors_count = fields.Integer(string='زوّار')
    summary = fields.Text(string='ملخّص الوردية')
    highlights = fields.Text(string='أبرز الأحداث')
    notes = fields.Text(string='ملاحظات وتوصيات')
    state = fields.Selection([('draft', 'مسودّة'), ('submitted', 'مُرسَل')],
                             default='draft', tracking=True)

    _sql_constraints = [
        ('guard_date_uniq', 'unique(guard_user_id, date)',
         'يوجد تقرير نشاط يومي لهذا الحارس في هذا التاريخ.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if not v.get('name') or v['name'] == '/':
                v['name'] = 'DAR-%s' % fields.Datetime.now().strftime('%Y%m%d-%H%M%S')
        return super().create(vals_list)
