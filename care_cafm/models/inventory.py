# -*- coding: utf-8 -*-
"""Internal inventory for CAFM: materials ordered FROM CARE are received into a
store, then issued/consumed to facilities (office, bathroom…). A field worker
can scan a product's barcode to consume it on the spot. Every movement adjusts
the per-store balance, with min/max reorder alerts and full traceability.

Design:
  care.cafm.store        — an internal store (central / per-facility / vehicle)
  care.cafm.stock.item   — a product's balance inside a store (min/max/low)
  care.cafm.stock.move   — receipt / issue / transfer / adjust / return
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class CafmStore(models.Model):
    _name = 'care.cafm.store'
    _description = 'CAFM Internal Store'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='المخزن', required=True, tracking=True)
    code = fields.Char(string='الرمز', copy=False, index=True)
    store_type = fields.Selection([
        ('central', 'مخزن مركزي'), ('facility', 'مخزن مرفق'), ('vehicle', 'مركبة/عهدة متنقّلة'),
    ], string='النوع', default='facility', required=True, tracking=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', tracking=True)
    keeper_id = fields.Many2one('hr.employee', string='أمين المخزن', tracking=True)
    item_ids = fields.One2many('care.cafm.stock.item', 'store_id', string='الأصناف')
    item_count = fields.Integer(string='عدد الأصناف', compute='_compute_stats')
    low_count = fields.Integer(string='أصناف منخفضة', compute='_compute_stats')
    stock_value = fields.Float(string='قيمة المخزون', compute='_compute_stats')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('item_ids', 'item_ids.on_hand', 'item_ids.low_stock', 'item_ids.stock_value')
    def _compute_stats(self):
        for s in self:
            s.item_count = len(s.item_ids)
            s.low_count = len(s.item_ids.filtered('low_stock'))
            s.stock_value = sum(s.item_ids.mapped('stock_value'))

    def action_view_items(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('أصناف %s') % self.name,
            'res_model': 'care.cafm.stock.item', 'view_mode': 'tree,form',
            'domain': [('store_id', '=', self.id)],
            'context': {'default_store_id': self.id},
        }


class CafmStockItem(models.Model):
    _name = 'care.cafm.stock.item'
    _description = 'CAFM Stock Item (balance)'
    _inherit = ['mail.thread']
    _order = 'store_id, product_id'
    _rec_name = 'product_id'

    store_id = fields.Many2one('care.cafm.store', string='المخزن', required=True, ondelete='cascade', index=True)
    facility_id = fields.Many2one(related='store_id.facility_id', store=True, string='المرفق')
    product_id = fields.Many2one('product.product', string='المنتج', required=True, ondelete='cascade', index=True)
    barcode = fields.Char(related='product_id.barcode', store=True, string='الباركود')
    default_code = fields.Char(related='product_id.default_code', string='الرمز الداخلي')
    uom_name = fields.Char(related='product_id.uom_id.name', string='الوحدة')
    on_hand = fields.Float(string='الرصيد', default=0.0, tracking=True)
    min_qty = fields.Float(string='حد إعادة الطلب', default=0.0)
    max_qty = fields.Float(string='الحد الأقصى', default=0.0)
    low_stock = fields.Boolean(string='منخفض', compute='_compute_flags', store=True)
    to_reorder = fields.Float(string='الكمية المقترحة للطلب', compute='_compute_flags', store=True)
    unit_cost = fields.Float(string='تكلفة الوحدة')
    stock_value = fields.Float(string='قيمة الرصيد', compute='_compute_value', store=True)
    last_move_date = fields.Datetime(string='آخر حركة', readonly=True)
    move_ids = fields.One2many('care.cafm.stock.move', 'item_id', string='الحركات')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('store_product_uniq', 'unique(store_id, product_id)',
         'هذا المنتج مُسجّل مسبقًا في هذا المخزن.'),
    ]

    @api.depends('on_hand', 'min_qty', 'max_qty')
    def _compute_flags(self):
        for it in self:
            it.low_stock = it.min_qty > 0 and it.on_hand <= it.min_qty
            target = it.max_qty if it.max_qty > 0 else it.min_qty
            it.to_reorder = max(0.0, target - it.on_hand) if it.low_stock else 0.0

    @api.depends('on_hand', 'unit_cost')
    def _compute_value(self):
        for it in self:
            it.stock_value = it.on_hand * (it.unit_cost or 0.0)

    @api.model
    def _get_or_create(self, store, product):
        item = self.search([('store_id', '=', store.id), ('product_id', '=', product.id)], limit=1)
        if not item:
            item = self.create({'store_id': store.id, 'product_id': product.id})
        return item

    def name_get(self):
        return [(it.id, '%s @ %s' % (it.product_id.display_name, it.store_id.name)) for it in self]

    def action_reorder(self):
        """Raise a CARE service request to restock this item back to CARE."""
        self.ensure_one()
        if 'care.cafm.service.request' not in self.env:
            raise UserError(_('نظام الطلبات غير متاح.'))
        req = self.env['care.cafm.service.request'].create({
            'title': _('إعادة طلب مخزون: %s') % self.product_id.display_name,
            'facility_id': self.facility_id.id or (self.store_id.facility_id.id or False),
            'description': _('طلب إعادة تخزين الكمية: %.2f %s (الرصيد الحالي %.2f)') % (
                self.to_reorder or self.min_qty, self.uom_name or '', self.on_hand),
        }) if self.facility_id or self.store_id.facility_id else None
        if not req:
            raise UserError(_('حدّد مرفقًا للمخزن أولاً.'))
        self.message_post(body=_('📦 أُنشئ طلب إعادة تخزين %s') % req.name)
        return {'type': 'ir.actions.act_window', 'res_model': 'care.cafm.service.request',
                'res_id': req.id, 'view_mode': 'form'}


class CafmStockMove(models.Model):
    _name = 'care.cafm.stock.move'
    _description = 'CAFM Stock Move'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char(string='المرجع', default='/', copy=False, readonly=True)
    move_type = fields.Selection([
        ('receipt', 'استلام (وارد)'), ('issue', 'صرف (منصرف)'),
        ('transfer', 'تحويل بين المخازن'), ('adjust', 'تسوية جرد'), ('return', 'إرجاع للمخزن'),
    ], string='نوع الحركة', default='issue', required=True, tracking=True)
    store_id = fields.Many2one('care.cafm.store', string='المخزن', required=True, tracking=True)
    product_id = fields.Many2one('product.product', string='المنتج', required=True, tracking=True)
    item_id = fields.Many2one('care.cafm.stock.item', string='صنف المخزون', readonly=True, ondelete='set null')
    quantity = fields.Float(string='الكمية', required=True, default=1.0)
    uom_name = fields.Char(related='product_id.uom_id.name', string='الوحدة')
    # destinations
    dest_store_id = fields.Many2one('care.cafm.store', string='المخزن المستلِم (تحويل)')
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق (صرف)', tracking=True)
    location_id = fields.Many2one('care.cafm.location', string='الموقع (مكتب/حمّام…)', tracking=True,
                                  domain="[('facility_id','=',facility_id)]")
    employee_id = fields.Many2one('hr.employee', string='المنفّذ/المستلِم', tracking=True)
    workorder_id = fields.Many2one('care.cafm.workorder', string='أمر العمل', ondelete='set null')
    partner_id = fields.Many2one('res.partner', string='المورّد/الجهة (استلام)')
    order_ref = fields.Char(string='مرجع الطلب')
    scan_code = fields.Char(string='الباركود الممسوح')
    unit_cost = fields.Float(string='تكلفة الوحدة')
    total_cost = fields.Float(string='الإجمالي', compute='_compute_total', store=True)
    expiry_date = fields.Date(string='تاريخ الانتهاء (للاستلام)')
    date = fields.Datetime(string='التاريخ', default=fields.Datetime.now, required=True)
    state = fields.Selection([('draft', 'مسودة'), ('done', 'مؤكّد')], default='draft', tracking=True)
    note = fields.Char(string='ملاحظة')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('quantity', 'unit_cost')
    def _compute_total(self):
        for m in self:
            m.total_cost = m.quantity * (m.unit_cost or 0.0)

    @api.constrains('quantity')
    def _check_qty(self):
        for m in self:
            if m.quantity <= 0:
                raise ValidationError(_('الكمية يجب أن تكون أكبر من صفر.'))

    @api.onchange('scan_code')
    def _onchange_scan(self):
        """Field flow: scanning a barcode auto-selects the product."""
        if self.scan_code:
            p = self.env['product.product'].search(
                ['|', ('barcode', '=', self.scan_code), ('default_code', '=', self.scan_code)], limit=1)
            if p:
                self.product_id = p

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        prefix = {'receipt': 'RCP', 'issue': 'ISS', 'transfer': 'TRF', 'adjust': 'ADJ', 'return': 'RET'}
        for m in moves:
            if not m.name or m.name == '/':
                m.name = '%s/%06d' % (prefix.get(m.move_type, 'MOV'), m.id)
        return moves

    def action_done(self):
        for m in self:
            if m.state == 'done':
                continue
            m._apply()
            m.state = 'done'

    def _apply(self):
        """Post the movement to the store balance(s)."""
        self.ensure_one()
        Item = self.env['care.cafm.stock.item']
        it = Item._get_or_create(self.store_id, self.product_id)
        self.item_id = it.id
        if self.unit_cost and not it.unit_cost:
            it.unit_cost = self.unit_cost
        if self.move_type in ('receipt', 'return', 'adjust'):
            it.on_hand += self.quantity
        elif self.move_type == 'issue':
            if self.quantity > it.on_hand:
                raise UserError(_('الرصيد غير كافٍ: المتاح %.2f فقط.') % it.on_hand)
            it.on_hand -= self.quantity
        elif self.move_type == 'transfer':
            if not self.dest_store_id:
                raise UserError(_('حدّد المخزن المستلِم للتحويل.'))
            if self.quantity > it.on_hand:
                raise UserError(_('الرصيد غير كافٍ للتحويل: المتاح %.2f.') % it.on_hand)
            it.on_hand -= self.quantity
            dest = Item._get_or_create(self.dest_store_id, self.product_id)
            dest.on_hand += self.quantity
            dest.last_move_date = fields.Datetime.now()
        it.last_move_date = fields.Datetime.now()
        # low-stock alert
        if it.low_stock:
            it.message_post(body=_('⚠️ الرصيد منخفض: %.2f (حد الطلب %.2f).') % (it.on_hand, it.min_qty))

    @api.model
    def scan_issue(self, store_id, barcode, quantity=1.0, facility_id=None, location_id=None, employee_id=None):
        """Field API: a worker scans a product barcode to consume it from a store."""
        store = self.env['care.cafm.store'].browse(int(store_id)).exists()
        if not store:
            raise UserError(_('المخزن غير موجود.'))
        p = self.env['product.product'].search(
            ['|', ('barcode', '=', barcode), ('default_code', '=', barcode)], limit=1)
        if not p:
            raise UserError(_('لا يوجد منتج بهذا الباركود: %s') % barcode)
        move = self.create({
            'move_type': 'issue', 'store_id': store.id, 'product_id': p.id,
            'quantity': quantity, 'scan_code': barcode,
            'facility_id': facility_id or store.facility_id.id or False,
            'location_id': location_id or False, 'employee_id': employee_id or False,
        })
        move.action_done()
        return move
