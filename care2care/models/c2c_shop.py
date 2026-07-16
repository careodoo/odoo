# -*- coding: utf-8 -*-
"""CARE 2 CARE product shop — customers buy materials/products from us.
A lightweight order over product.product with delivery + payment."""
from odoo import api, fields, models, _


class C2CProductOrder(models.Model):
    _name = 'c2c.product.order'
    _description = 'CARE 2 CARE Product Order'
    # activity.mixin so a customer cancel request can raise a real To-Do
    _inherit = ['mail.thread', 'mail.activity.mixin', 'c2c.team.notify.mixin']
    _order = 'create_date desc, id desc'
    _notify_setting_field = 'order_notify_user_ids'
    _notify_action_prefix = 'c2c/order'

    name = fields.Char(string='رقم الطلب', default='/', copy=False, readonly=True)
    partner_id = fields.Many2one('res.partner', string='العميل', required=True,
                                 default=lambda s: s.env.user.partner_id)
    line_ids = fields.One2many('c2c.product.order.line', 'order_id', string='المنتجات')
    amount_total = fields.Float(string='الإجمالي', compute='_compute_total', store=True)
    item_count = fields.Integer(string='عدد الأصناف', compute='_compute_total', store=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    address = fields.Char(string='عنوان التوصيل')
    area = fields.Char(string='المنطقة')
    phone = fields.Char(string='الهاتف')
    address_id = fields.Many2one('c2c.delivery.address', string='عنوان محفوظ')
    payment_method = fields.Selection([
        ('cash', 'نقدًا عند الاستلام'), ('knet', 'كي نت'), ('card', 'بطاقة'), ('wallet', 'المحفظة'),
    ], string='طريقة الدفع', default='cash', tracking=True)
    payment_state = fields.Selection([('unpaid', 'غير مدفوع'), ('paid', 'مدفوع')], default='unpaid', tracking=True)
    state = fields.Selection([
        ('draft', 'قيد المعالجة'), ('confirmed', 'مؤكّد'), ('shipped', 'قيد التوصيل'),
        ('delivered', 'تم التسليم'), ('cancelled', 'ملغى'),
    ], string='الحالة', default='draft', required=True, tracking=True)
    note = fields.Text(string='ملاحظات')
    cancel_requested = fields.Boolean(string='طلب إلغاء', tracking=True)
    cancel_reason = fields.Char(string='سبب الإلغاء')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('line_ids.subtotal')
    def _compute_total(self):
        for o in self:
            o.amount_total = sum(o.line_ids.mapped('subtotal'))
            o.item_count = int(sum(o.line_ids.mapped('quantity')))

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        for r in recs:
            if not r.name or r.name == '/':
                r.name = self.env['ir.sequence'].next_by_code('c2c.product.order') or ('SHOP-%06d' % r.id)
        return recs

    # ---- notifications -----------------------------------------------------
    # customer-facing push per state (mirrors c2c.booking._CUST_MSG)
    _CUST_MSG = {
        'confirmed': ('✅ تم تأكيد طلبك', 'تم تأكيد طلبك %s وجارٍ تجهيزه.'),
        'shipped': ('🚚 طلبك في الطريق', 'طلبك %s خرج للتوصيل.'),
        'delivered': ('🎉 تم تسليم طلبك', 'تم تسليم طلبك %s. شكرًا لثقتك.'),
        'cancelled': ('✖ تم إلغاء الطلب', 'تم إلغاء طلبك %s.'),
    }

    def _notify_customer(self, state):
        self.ensure_one()
        msg = self._CUST_MSG.get(state)
        if not msg or 'care.cafm.notification' not in self.env or not self.partner_id:
            return
        users = self.env['res.users'].sudo().search([('partner_id', '=', self.partner_id.id)])
        if not users:
            return
        title, tpl = msg
        try:
            self.env['care.cafm.notification'].sudo().push(
                users, title, tpl % (self.name or ''), ntype='info',
                action_url='c2c/order/%s' % self.id)
        except Exception:
            pass

    # _notify_team comes from c2c.team.notify.mixin

    # ---- lifecycle ---------------------------------------------------------
    def action_confirm(self):
        self.write({'state': 'confirmed'})
        for o in self:
            o._notify_customer('confirmed')
            o._notify_team(_('🛒 طلب متجر جديد'),
                           _('طلب جديد %s من %s بإجمالي %.2f') % (
                               o.name or '', o.partner_id.display_name or '', o.amount_total or 0.0))

    def action_ship(self):
        self.write({'state': 'shipped'})
        for o in self:
            o.message_post(body=_('🚚 خرج الطلب للتوصيل'))
            o._notify_customer('shipped')

    def action_deliver(self):
        self.write({'state': 'delivered'})
        for o in self:
            o.message_post(body=_('🎉 تم تسليم الطلب'))
            o._notify_customer('delivered')

    def action_cancel(self):
        self.write({'state': 'cancelled', 'cancel_requested': False})
        for o in self:
            o._notify_customer('cancelled')

    def action_reject_cancel(self):
        self.write({'cancel_requested': False})
        for o in self:
            o.message_post(body=_('تم رفض طلب الإلغاء — الطلب مستمر.'))

    def request_cancel(self, reason=None):
        """Customer-initiated cancel request from the app/portal."""
        self.ensure_one()
        if self.state in ('delivered', 'cancelled'):
            return False
        # while still un-processed the customer may cancel outright
        if self.state in ('draft', 'confirmed'):
            self.write({'state': 'cancelled', 'cancel_requested': False,
                        'cancel_reason': reason or self.cancel_reason})
            self.message_post(body=_('ألغى العميل الطلب%s') % ((': %s' % reason) if reason else ''))
            self._notify_customer('cancelled')
            self._notify_team(_('✖ ألغى عميل طلبه'),
                              _('ألغى %s الطلب %s%s') % (self.partner_id.display_name or '',
                                                          self.name or '', (' — %s' % reason) if reason else ''))
        else:
            # already shipped → needs a human decision, so raise an activity
            self.write({'cancel_requested': True, 'cancel_reason': reason or self.cancel_reason})
            self.message_post(body=_('طلب العميل إلغاء الطلب%s') % ((': %s' % reason) if reason else ''))
            self._notify_team(_('⚠ طلب إلغاء يحتاج مراجعة'),
                              _('طلب %s إلغاء الطلب %s بعد خروجه للتوصيل%s') % (
                                  self.partner_id.display_name or '', self.name or '',
                                  (' — %s' % reason) if reason else ''),
                              activity=True)
        return True

    # progress index for the app timeline (cancelled = -1)
    STAGE_FLOW = ['draft', 'confirmed', 'shipped', 'delivered']

    def progress_index(self):
        self.ensure_one()
        if self.state == 'cancelled':
            return -1
        try:
            return self.STAGE_FLOW.index(self.state)
        except ValueError:
            return 0


class C2CDeliveryAddress(models.Model):
    _name = 'c2c.delivery.address'
    _description = 'CARE 2 CARE Delivery Address'
    _order = 'is_default desc, id desc'

    partner_id = fields.Many2one('res.partner', string='العميل', required=True, ondelete='cascade',
                                 default=lambda s: s.env.user.partner_id, index=True)
    label = fields.Char(string='الاسم', required=True, help='مثل: المنزل، العمل')
    area = fields.Char(string='المنطقة')
    block = fields.Char(string='القطعة')
    street = fields.Char(string='الشارع')
    building = fields.Char(string='المبنى / المنزل')
    floor = fields.Char(string='الدور')
    apartment = fields.Char(string='الشقة')
    landmark = fields.Char(string='علامة مميزة')
    phone = fields.Char(string='الهاتف')
    notes = fields.Char(string='ملاحظات إضافية')
    is_default = fields.Boolean(string='افتراضي')
    active = fields.Boolean(default=True)
    full_address = fields.Char(string='العنوان الكامل', compute='_compute_full', store=True)

    @api.depends('area', 'block', 'street', 'building', 'floor', 'apartment', 'landmark')
    def _compute_full(self):
        for a in self:
            parts = []
            if a.area:
                parts.append(a.area)
            if a.block:
                parts.append('قطعة %s' % a.block)
            if a.street:
                parts.append('شارع %s' % a.street)
            if a.building:
                parts.append('مبنى %s' % a.building)
            if a.floor:
                parts.append('دور %s' % a.floor)
            if a.apartment:
                parts.append('شقة %s' % a.apartment)
            if a.landmark:
                parts.append(a.landmark)
            a.full_address = '، '.join(parts)

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        for r in recs:
            r._enforce_single_default()
        return recs

    def write(self, vals):
        res = super().write(vals)
        if vals.get('is_default'):
            for r in self:
                r._enforce_single_default()
        return res

    def _enforce_single_default(self):
        if self.is_default:
            self.search([('partner_id', '=', self.partner_id.id), ('id', '!=', self.id),
                         ('is_default', '=', True)]).write({'is_default': False})


class C2CProductOrderLine(models.Model):
    _name = 'c2c.product.order.line'
    _description = 'CARE 2 CARE Product Order Line'

    order_id = fields.Many2one('c2c.product.order', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='المنتج', required=True)
    quantity = fields.Float(string='الكمية', default=1.0, required=True)
    price_unit = fields.Float(string='السعر')
    subtotal = fields.Float(string='الإجمالي', compute='_compute_sub', store=True)

    @api.depends('quantity', 'price_unit')
    def _compute_sub(self):
        for l in self:
            l.subtotal = l.quantity * l.price_unit

    @api.onchange('product_id')
    def _onchange_product(self):
        if self.product_id and not self.price_unit:
            self.price_unit = self.product_id.lst_price
