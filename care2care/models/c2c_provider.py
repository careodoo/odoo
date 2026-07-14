# -*- coding: utf-8 -*-
"""CARE 2 CARE service provider (technician/crew) that fulfils bookings."""
from odoo import api, fields, models


class C2CProvider(models.Model):
    _name = 'c2c.provider'
    _description = 'CARE 2 CARE Provider'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='مقدّم الخدمة', required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='الموظف')
    phone = fields.Char(string='الهاتف')
    category_ids = fields.Many2many('c2c.category', string='الفئات المؤهّل لها')
    image = fields.Image(string='صورة', max_width=512, max_height=512)
    booking_ids = fields.One2many('c2c.booking', 'provider_id', string='الحجوزات')
    booking_count = fields.Integer(compute='_compute_stats')
    rating_avg = fields.Float(string='متوسط التقييم', compute='_compute_stats')
    available = fields.Boolean(string='متاح', default=True, tracking=True)
    active = fields.Boolean(default=True)

    @api.depends('booking_ids', 'booking_ids.rating')
    def _compute_stats(self):
        for p in self:
            p.booking_count = len(p.booking_ids)
            rated = p.booking_ids.filtered(lambda b: b.rating)
            p.rating_avg = round(sum(int(b.rating) for b in rated) / len(rated), 1) if rated else 0.0
