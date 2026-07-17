# -*- coding: utf-8 -*-
"""CARE 2 CARE professional extras: customer reviews, before/after work
galleries, monthly subscription plans and time-boxed offers/promotions."""
from odoo import api, fields, models, _


class C2CReview(models.Model):
    _name = 'c2c.review'
    _description = 'CARE 2 CARE Review'
    _inherit = ['mail.thread']
    _order = 'featured desc, date desc, id desc'

    service_id = fields.Many2one('c2c.service', string='الخدمة', ondelete='cascade', index=True)
    author_name = fields.Char(string='العميل', required=True)
    avatar = fields.Image(string='صورة العميل', max_width=256, max_height=256)
    rating = fields.Selection([('1', '★'), ('2', '★★'), ('3', '★★★'), ('4', '★★★★'), ('5', '★★★★★')],
                              string='التقييم', default='5', required=True)
    comment = fields.Text(string='التعليق')
    date = fields.Date(string='التاريخ', default=fields.Date.context_today)
    featured = fields.Boolean(string='مميّز (يظهر في الرئيسية)')
    partner_id = fields.Many2one('res.partner', string='صاحب التقييم')
    booking_id = fields.Many2one('c2c.booking', string='الحجز', ondelete='set null')
    state = fields.Selection([
        ('pending', 'بانتظار الاعتماد'), ('approved', 'معتمد'), ('rejected', 'مرفوض'),
    ], string='الحالة', default='pending', required=True, tracking=True)
    moderated_by = fields.Many2one('res.users', string='اعتمده', readonly=True)
    active = fields.Boolean(default=True)

    def action_approve(self):
        self.write({'state': 'approved', 'moderated_by': self.env.uid})

    def action_reject(self):
        self.write({'state': 'rejected', 'moderated_by': self.env.uid})


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


class C2CSubscriptionRequest(models.Model):
    """A customer subscribes to a plan → a request the team reviews and can turn
    into an active subscription (and, later, a CAFM contract). Same lifecycle
    shape as c2c.contract.request so the back office handles both the same way."""
    _name = 'c2c.subscription.request'
    _description = 'CARE 2 CARE Subscription Request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'c2c.team.notify.mixin']
    _order = 'create_date desc, id desc'
    _notify_setting_field = 'contract_notify_user_ids'
    _notify_action_prefix = 'c2c/subscription'

    name = fields.Char(string='رقم الطلب', default='/', copy=False, readonly=True)
    partner_id = fields.Many2one('res.partner', string='العميل',
                                 default=lambda s: s.env.user.partner_id if not s.env.user._is_public() else False)
    plan_id = fields.Many2one('c2c.subscription.plan', string='الباقة', required=True, ondelete='restrict')
    customer_name = fields.Char(string='الاسم', required=True)
    phone = fields.Char(string='الهاتف', required=True)
    address_id = fields.Many2one('c2c.delivery.address', string='العنوان')
    note = fields.Text(string='ملاحظات')
    # snapshot of the plan at subscribe time, so a later price change doesn't
    # silently rewrite what the customer signed up for
    period = fields.Selection(related='plan_id.period', store=True, readonly=True)
    price = fields.Float(string='السعر', readonly=True)
    visits = fields.Integer(string='عدد الزيارات', readonly=True)
    start_date = fields.Date(string='تاريخ البدء', default=fields.Date.context_today)
    state = fields.Selection([
        ('new', 'جديد'), ('active', 'مُفعَّل'), ('paused', 'موقوف'),
        ('converted', 'محوّل لعقد'), ('cancelled', 'ملغى'),
    ], string='الحالة', default='new', required=True, tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', '/') == '/':
                v['name'] = self.env['ir.sequence'].next_by_code('c2c.subscription.request') or _('طلب اشتراك')
            # snapshot the plan's price/visits at subscribe time
            if v.get('plan_id') and not v.get('price'):
                plan = self.env['c2c.subscription.plan'].browse(v['plan_id'])
                v.setdefault('price', plan.price)
                v.setdefault('visits', plan.visits)
        recs = super().create(vals_list)
        for r in recs:
            r._notify_team(_('🔔 طلب اشتراك جديد'),
                           _('اشتراك جديد %s في باقة «%s» من %s (%s)') % (
                               r.name or '', r.plan_id.name or '', r.customer_name or '', r.phone or ''),
                           activity=True)
        return recs

    def action_activate(self):
        self.write({'state': 'active'})

    def action_pause(self):
        self.write({'state': 'paused'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})


class C2CServiceMedia(models.Model):
    """Photos and videos shown inside a service page — the professional gallery
    the customer browses before booking."""
    _name = 'c2c.service.media'
    _description = 'CARE 2 CARE Service Media'
    _order = 'sequence, id'

    service_id = fields.Many2one('c2c.service', string='الخدمة', ondelete='cascade', index=True)
    name = fields.Char(string='العنوان', translate=True)
    kind = fields.Selection([('image', 'صورة'), ('video', 'فيديو')], string='النوع',
                            default='image', required=True)
    image = fields.Image(string='الصورة', max_width=1600, max_height=1200)
    video_url = fields.Char(string='رابط الفيديو (mp4/youtube)')
    poster = fields.Image(string='صورة الغلاف (للفيديو)', max_width=1280, max_height=720)
    featured = fields.Boolean(string='يظهر في بلوك الفيديوهات بالرئيسية')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
