# -*- coding: utf-8 -*-
"""CARE 2 CARE service catalogue: categories → services → packages/pricing.
Home & company on-demand services (cleaning, carpet & laundry, maintenance…)."""
from odoo import api, fields, models


class C2CCategory(models.Model):
    _name = 'c2c.category'
    _description = 'CARE 2 CARE Service Category'
    _order = 'sequence, name'

    name = fields.Char(string='الفئة', required=True, translate=True)
    icon = fields.Char(string='أيقونة (إيموجي)', default='🧹')
    image = fields.Image(string='صورة', max_width=1024, max_height=1024)
    color = fields.Char(string='لون', default='#0e3a5f')
    sequence = fields.Integer(default=10)
    show_on_home = fields.Boolean(
        string='تظهر في الرئيسية', default=True,
        help='تحكّم في أي الفئات تظهر ضمن أيقونات الصفحة الرئيسية للتطبيق. '
             'أزل العلامة لإخفائها من الرئيسية مع إبقائها متاحة داخل «كل الخدمات».')
    service_ids = fields.One2many('c2c.service', 'category_id', string='الخدمات')
    service_count = fields.Integer(compute='_compute_count')
    active = fields.Boolean(default=True)

    @api.depends('service_ids')
    def _compute_count(self):
        for c in self:
            c.service_count = len(c.service_ids)


class C2CService(models.Model):
    _name = 'c2c.service'
    _description = 'CARE 2 CARE Service'
    _inherit = ['mail.thread']
    _order = 'category_id, sequence, name'

    name = fields.Char(string='الخدمة', required=True, translate=True, tracking=True)
    category_id = fields.Many2one('c2c.category', string='الفئة', required=True, tracking=True)
    image = fields.Image(string='صورة', max_width=1024, max_height=1024)
    description = fields.Text(string='الوصف', translate=True)
    audience = fields.Selection([
        ('home', 'منازل'), ('company', 'شركات'), ('both', 'الاثنان'),
    ], string='الفئة المستهدفة', default='both', tracking=True)
    base_price = fields.Float(string='السعر الأساسي', tracking=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    price_unit = fields.Selection([
        ('visit', 'لكل زيارة'), ('hour', 'لكل ساعة'), ('unit', 'لكل قطعة'), ('sqm', 'لكل م²'),
    ], string='وحدة التسعير', default='visit')
    duration_min = fields.Integer(string='المدة المقدّرة (دقيقة)', default=60)
    rating_avg = fields.Float(string='متوسط التقييم', compute='_compute_rating', store=True)
    booking_count = fields.Integer(string='عدد الحجوزات', compute='_compute_rating', store=True)
    package_ids = fields.One2many('c2c.service.package', 'service_id', string='الباقات')
    sequence = fields.Integer(default=10)
    popular = fields.Boolean(string='الأكثر طلبًا', tracking=True)
    active = fields.Boolean(default=True)

    @api.depends('name')
    def _compute_rating(self):
        Booking = self.env['c2c.booking']
        for s in self:
            bks = Booking.search([('service_id', '=', s.id)])
            s.booking_count = len(bks)
            rated = bks.filtered(lambda b: b.rating)
            s.rating_avg = round(sum(int(r.rating) for r in rated) / len(rated), 1) if rated else 0.0


class C2CServicePackage(models.Model):
    _name = 'c2c.service.package'
    _description = 'CARE 2 CARE Service Package'
    _order = 'price'

    service_id = fields.Many2one('c2c.service', string='الخدمة', required=True, ondelete='cascade')
    name = fields.Char(string='الباقة', required=True, translate=True)
    description = fields.Char(string='ما تشمله', translate=True)
    price = fields.Float(string='السعر', required=True)
    duration_min = fields.Integer(string='المدة (دقيقة)', default=60)
    active = fields.Boolean(default=True)
