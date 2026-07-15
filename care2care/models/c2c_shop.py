# -*- coding: utf-8 -*-
"""CARE 2 CARE product shop — customers buy materials/products from us.
A lightweight order over product.product with delivery + payment."""
from odoo import api, fields, models, _


class C2CProductOrder(models.Model):
    _name = 'c2c.product.order'
    _description = 'CARE 2 CARE Product Order'
    _inherit = ['mail.thread']
    _order = 'create_date desc, id desc'

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
    payment_method = fields.Selection([
        ('cash', 'نقدًا عند الاستلام'), ('knet', 'كي نت'), ('card', 'بطاقة'), ('wallet', 'المحفظة'),
    ], string='طريقة الدفع', default='cash', tracking=True)
    payment_state = fields.Selection([('unpaid', 'غير مدفوع'), ('paid', 'مدفوع')], default='unpaid', tracking=True)
    state = fields.Selection([
        ('draft', 'قيد المعالجة'), ('confirmed', 'مؤكّد'), ('shipped', 'قيد التوصيل'),
        ('delivered', 'تم التسليم'), ('cancelled', 'ملغى'),
    ], string='الحالة', default='draft', required=True, tracking=True)
    note = fields.Text(string='ملاحظات')
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

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})


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
