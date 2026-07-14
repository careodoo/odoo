# -*- coding: utf-8 -*-
"""CARE 2 CARE professional extras: customer reviews, before/after work
galleries, monthly subscription plans and time-boxed offers/promotions."""
from odoo import api, fields, models


class C2CReview(models.Model):
    _name = 'c2c.review'
    _description = 'CARE 2 CARE Review'
    _order = 'featured desc, date desc, id desc'

    service_id = fields.Many2one('c2c.service', string='الخدمة', ondelete='cascade', index=True)
    author_name = fields.Char(string='العميل', required=True)
    avatar = fields.Image(string='صورة العميل', max_width=256, max_height=256)
    rating = fields.Selection([('1', '★'), ('2', '★★'), ('3', '★★★'), ('4', '★★★★'), ('5', '★★★★★')],
                              string='التقييم', default='5', required=True)
    comment = fields.Text(string='التعليق')
    date = fields.Date(string='التاريخ', default=fields.Date.context_today)
    featured = fields.Boolean(string='مميّز (يظهر في الرئيسية)')
    active = fields.Boolean(default=True)


class C2CWorkSample(models.Model):
    """Before/after showcase of previous work for a service."""
    _name = 'c2c.work.sample'
    _description = 'CARE 2 CARE Work Sample (before/after)'
    _order = 'date desc, id desc'

    service_id = fields.Many2one('c2c.service', string='الخدمة', ondelete='cascade', index=True)
    title = fields.Char(string='العنوان', required=True)
    before_image = fields.Image(string='قبل', max_width=1024, max_height=1024)
    after_image = fields.Image(string='بعد', max_width=1024, max_height=1024)
    note = fields.Char(string='ملاحظة')
    date = fields.Date(string='التاريخ', default=fields.Date.context_today)
    active = fields.Boolean(default=True)


class C2CSubscriptionPlan(models.Model):
    """A recurring subscription (e.g. monthly cleaning) at a saved price."""
    _name = 'c2c.subscription.plan'
    _description = 'CARE 2 CARE Subscription Plan'
    _order = 'sequence, price'

    name = fields.Char(string='الباقة', required=True, translate=True)
    category_id = fields.Many2one('c2c.category', string='الفئة')
    service_id = fields.Many2one('c2c.service', string='الخدمة')
    image = fields.Image(string='صورة', max_width=1024, max_height=1024)
    period = fields.Selection([('monthly', 'شهري'), ('quarterly', 'ربع سنوي'), ('yearly', 'سنوي')],
                              string='الدورة', default='monthly', required=True)
    visits = fields.Integer(string='عدد الزيارات', default=4)
    price = fields.Float(string='السعر', required=True)
    old_price = fields.Float(string='السعر قبل الخصم')
    save_pct = fields.Integer(string='نسبة التوفير %', compute='_compute_save', store=True)
    features = fields.Text(string='المزايا (سطر لكل ميزة)')
    color = fields.Char(string='لون', default='#0e3a5f')
    popular = fields.Boolean(string='الأفضل قيمة')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    @api.depends('price', 'old_price')
    def _compute_save(self):
        for p in self:
            p.save_pct = int(round(100 * (p.old_price - p.price) / p.old_price)) if p.old_price and p.old_price > p.price else 0


class C2COffer(models.Model):
    """A promotion: monthly / yearly / occasion-based discount."""
    _name = 'c2c.offer'
    _description = 'CARE 2 CARE Offer'
    _order = 'sequence, id desc'

    title = fields.Char(string='العرض', required=True, translate=True)
    subtitle = fields.Char(string='وصف مختصر', translate=True)
    description = fields.Text(string='التفاصيل', translate=True)
    image = fields.Image(string='صورة', max_width=1200, max_height=800)
    icon = fields.Char(string='أيقونة', default='🎉')
    kind = fields.Selection([('monthly', 'شهري'), ('yearly', 'سنوي'), ('occasion', 'مناسبة')],
                            string='النوع', default='monthly', required=True)
    discount_pct = fields.Integer(string='نسبة الخصم %')
    code = fields.Char(string='كود الخصم')
    color = fields.Char(string='لون', default='#0e3a5f')
    color2 = fields.Char(string='لون 2', default='#17547f')
    date_from = fields.Date(string='من')
    date_to = fields.Date(string='إلى')
    is_live = fields.Boolean(string='ساري', compute='_compute_live', search='_search_live')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    def _compute_live(self):
        today = fields.Date.context_today(self)
        for o in self:
            o.is_live = (not o.date_from or o.date_from <= today) and (not o.date_to or o.date_to >= today)

    def _search_live(self, operator, value):
        today = fields.Date.context_today(self)
        recs = self.search(['|', ('date_from', '=', False), ('date_from', '<=', today)]).filtered(
            lambda o: not o.date_to or o.date_to >= today)
        want = (operator == '=' and value) or (operator == '!=' and not value)
        return [('id', 'in' if want else 'not in', recs.ids)]
