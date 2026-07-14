# -*- coding: utf-8 -*-
"""Client feedback loop: the client rates a completed work order (1–5 stars)
and leaves a comment — a professional quality signal per service/worker that
feeds satisfaction reporting."""
from odoo import api, fields, models


class CafmWorkorder(models.Model):
    _inherit = 'care.cafm.workorder'

    client_rating = fields.Selection([
        ('1', '★'), ('2', '★★'), ('3', '★★★'), ('4', '★★★★'), ('5', '★★★★★'),
    ], string='تقييم العميل', tracking=True, index=True)
    client_rating_num = fields.Integer(string='التقييم (رقمي)', compute='_compute_rating_num', store=True)
    client_feedback = fields.Text(string='ملاحظات العميل')
    client_rated_date = fields.Datetime(string='تاريخ التقييم', readonly=True)

    @api.depends('client_rating')
    def _compute_rating_num(self):
        for w in self:
            w.client_rating_num = int(w.client_rating) if w.client_rating else 0
