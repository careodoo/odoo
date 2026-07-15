# -*- coding: utf-8 -*-
"""CARE 2 CARE booking: a customer books a service, picks a visit date/time,
address and pays. Lifecycle: draft → confirmed → assigned → in_progress →
done → (rated) / cancelled."""
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class C2CBooking(models.Model):
    _name = 'c2c.booking'
    _description = 'CARE 2 CARE Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'visit_datetime desc, id desc'

    name = fields.Char(string='رقم الحجز', default='/', copy=False, readonly=True)
    partner_id = fields.Many2one('res.partner', string='العميل', required=True, tracking=True,
                                 default=lambda s: s.env.user.partner_id)
    service_id = fields.Many2one('c2c.service', string='الخدمة', required=True, tracking=True)
    package_id = fields.Many2one('c2c.service.package', string='الباقة',
                                 domain="[('service_id','=',service_id)]")
    category_id = fields.Many2one(related='service_id.category_id', store=True, string='الفئة')
    # scheduling
    visit_datetime = fields.Datetime(string='موعد الزيارة', required=True, tracking=True,
                                     default=lambda s: fields.Datetime.now() + timedelta(days=1))
    duration_min = fields.Integer(string='المدة (دقيقة)')
    end_datetime = fields.Datetime(string='وقت الانتهاء المتوقّع', compute='_compute_end', store=True)
    # location
    address = fields.Char(string='العنوان', tracking=True)
    area = fields.Char(string='المنطقة')
    gps = fields.Char(string='الإحداثيات (GPS)')
    phone = fields.Char(string='هاتف التواصل')
    notes = fields.Text(string='ملاحظات العميل')
    # assignment
    provider_id = fields.Many2one('c2c.provider', string='مقدّم الخدمة', tracking=True)
    # pricing & payment
    amount = fields.Float(string='المبلغ', tracking=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    payment_method = fields.Selection([
        ('cash', 'نقدًا عند الزيارة'), ('knet', 'كي نت'), ('card', 'بطاقة'), ('wallet', 'المحفظة'),
    ], string='طريقة الدفع', default='cash', tracking=True)
    payment_state = fields.Selection([
        ('unpaid', 'غير مدفوع'), ('paid', 'مدفوع'), ('refunded', 'مُسترجع'),
    ], string='حالة الدفع', default='unpaid', tracking=True)
    discount_code = fields.Char(string='كود الخصم')
    discount_amount = fields.Float(string='قيمة الخصم')
    state = fields.Selection([
        ('draft', 'مسودة'), ('confirmed', 'مؤكّد'), ('assigned', 'مُسند'),
        ('in_progress', 'قيد التنفيذ'), ('done', 'منجز'), ('cancelled', 'ملغى'),
    ], string='الحالة', default='draft', required=True, tracking=True)
    rating = fields.Selection([
        ('1', '★'), ('2', '★★'), ('3', '★★★'), ('4', '★★★★'), ('5', '★★★★★'),
    ], string='التقييم', tracking=True)
    feedback = fields.Text(string='ملاحظات التقييم')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    # ---- field-execution (filled by the crew from the app) ----------------
    started_at = fields.Datetime(string='بدء التنفيذ', readonly=True, copy=False)
    finished_at = fields.Datetime(string='انتهاء التنفيذ', readonly=True, copy=False)
    staff_note = fields.Text(string='ملاحظة الفريق')
    proof_before = fields.Image(string='صورة قبل', max_width=1280, max_height=1280)
    proof_after = fields.Image(string='صورة بعد', max_width=1280, max_height=1280)
    quality_ok = fields.Boolean(string='اعتماد الجودة', tracking=True)
    quality_by = fields.Many2one('c2c.provider', string='اعتمد الجودة', readonly=True, copy=False)

    @api.depends('visit_datetime', 'duration_min')
    def _compute_end(self):
        for b in self:
            b.end_datetime = (b.visit_datetime + timedelta(minutes=b.duration_min or 0)) if b.visit_datetime else False

    @api.onchange('service_id', 'package_id')
    def _onchange_service(self):
        if self.package_id:
            self.amount = self.package_id.price
            self.duration_min = self.package_id.duration_min
        elif self.service_id:
            self.amount = self.service_id.base_price
            self.duration_min = self.service_id.duration_min

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', '/') == '/':
                v['name'] = self.env['ir.sequence'].next_by_code('c2c.booking') or _('حجز جديد')
            # default amount from service/package if not set
            if not v.get('amount'):
                pkg = self.env['c2c.service.package'].browse(v['package_id']) if v.get('package_id') else None
                svc = self.env['c2c.service'].browse(v['service_id']) if v.get('service_id') else None
                v['amount'] = (pkg.price if pkg else 0.0) or (svc.base_price if svc else 0.0)
            if not v.get('duration_min'):
                pkg = self.env['c2c.service.package'].browse(v['package_id']) if v.get('package_id') else None
                svc = self.env['c2c.service'].browse(v['service_id']) if v.get('service_id') else None
                v['duration_min'] = (pkg.duration_min if pkg else 0) or (svc.duration_min if svc else 60)
        return super().create(vals_list)

    def action_confirm(self):
        self.write({'state': 'confirmed'})
        for b in self:
            b.message_post(body=_('✅ تم تأكيد الحجز لموعد %s') % (b.visit_datetime or ''))

    def action_assign(self, provider=None):
        for b in self:
            if provider:
                b.provider_id = provider
            if not b.provider_id:
                raise UserError(_('اختر مقدّم خدمة أولاً.'))
            b.state = 'assigned'

    def action_start(self):
        for b in self:
            b.write({'state': 'in_progress', 'started_at': b.started_at or fields.Datetime.now()})

    def action_done(self):
        for b in self:
            b.write({'state': 'done', 'finished_at': fields.Datetime.now()})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_pay(self):
        self.write({'payment_state': 'paid'})
        for b in self:
            b.message_post(body=_('💳 تم استلام الدفع: %.2f') % b.amount)

    def action_rate(self, stars, feedback=None):
        self.ensure_one()
        self.write({'rating': str(stars), 'feedback': feedback or self.feedback})
        self.service_id._compute_rating()
