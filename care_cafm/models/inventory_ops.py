# -*- coding: utf-8 -*-
"""The two loops a stock system is not a stock system without.

Balances, issues and moves already existed. What was missing is what closes the
loop around them: counting what is physically on the shelf and reconciling the
difference, and getting more of something before it runs out. Without the first
the numbers drift until nobody trusts them; without the second the store
discovers it is empty at the moment someone needs the thing.
"""
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockCount(models.Model):
    """A physical count. The variance is the point — a count that silently
    overwrites the book figure teaches you nothing about why it drifted."""
    _name = 'care.cafm.stock.count'
    _description = 'جرد مخزني'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'count_date desc, id desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    store_id = fields.Many2one('care.cafm.store', string='المخزن', required=True,
                               tracking=True, index=True)
    facility_id = fields.Many2one(related='store_id.facility_id', store=True, index=True)
    count_date = fields.Date(string='تاريخ الجرد', default=fields.Date.context_today,
                             required=True, tracking=True)
    counted_by = fields.Many2one('hr.employee', string='القائم بالجرد', tracking=True)
    count_type = fields.Selection([
        ('full', 'جرد شامل'), ('cycle', 'جرد دوري جزئي'), ('spot', 'جرد مفاجئ'),
    ], string='نوع الجرد', default='cycle', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'قيد العدّ'), ('review', 'بانتظار الاعتماد'), ('done', 'مُعتمَد'),
        ('cancelled', 'ملغى'),
    ], string='الحالة', default='draft', required=True, tracking=True)
    line_ids = fields.One2many('care.cafm.stock.count.line', 'count_id', string='البنود')
    note = fields.Text(string='ملاحظات')

    line_count = fields.Integer(string='عدد البنود', compute='_compute_totals', store=True)
    variance_lines = fields.Integer(string='بنود بها فروقات', compute='_compute_totals', store=True)
    variance_value = fields.Float(string='قيمة الفروقات', compute='_compute_totals', store=True)
    accuracy = fields.Float(string='دقة المخزون %', compute='_compute_totals', store=True,
                            help='نسبة البنود التي طابق فيها العدّ الرصيد الدفتري.')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.cafm.stock.count') or '/'
        return super().create(vals_list)

    @api.depends('line_ids.variance', 'line_ids.variance_value')
    def _compute_totals(self):
        for c in self:
            lines = c.line_ids
            c.line_count = len(lines)
            off = lines.filtered(lambda l: abs(l.variance) > 0.0001)
            c.variance_lines = len(off)
            c.variance_value = sum(off.mapped('variance_value'))
            c.accuracy = (100.0 * (len(lines) - len(off)) / len(lines)) if lines else 0.0

    def action_load_items(self):
        """Pull the store's whole item list onto the sheet. Counting only what
        you remembered to add is how shortages hide."""
        for c in self:
            existing = set(c.line_ids.mapped('item_id').ids)
            items = self.env['care.cafm.stock.item'].sudo().search(
                [('store_id', '=', c.store_id.id)])
            c.line_ids = [(0, 0, {'item_id': i.id, 'counted_qty': 0.0})
                          for i in items if i.id not in existing]
        return True

    def action_review(self):
        for c in self:
            if not c.line_ids:
                raise UserError(_('حمّل بنود المخزن أولًا.'))
            missing = c.line_ids.filtered(lambda l: not l.counted)
            if missing:
                raise UserError(_(
                    'بقي %d بندًا دون عدّ. اعتماد ورقة ناقصة يُسجّل عجزًا كاملًا '
                    'على أصناف موجودة فعلًا على الرفّ.\nأولها: %s')
                    % (len(missing), ', '.join(
                        missing[:5].mapped(lambda l: l.item_id.display_name))))
            c.state = 'review'

    def action_approve(self):
        """Approving posts an adjustment move for each difference, so the
        balance changes through the ledger and not behind it."""
        Move = self.env['care.cafm.stock.move'].sudo()
        for c in self:
            if c.state != 'review':
                raise UserError(_('يُعتمد الجرد بعد مراجعته فقط.'))
            # The ledger moves the balance — never a direct write to on_hand,
            # or the stock card stops explaining how it got where it is. Moves
            # only carry positive quantities, so a shortage posts as an issue
            # and a surplus as an adjustment.
            moves = Move.browse()
            for l in c.line_ids.filtered(lambda x: abs(x.variance) > 0.0001):
                gain = l.variance > 0
                moves |= Move.create({
                    'move_type': 'adjust' if gain else 'issue',
                    'store_id': c.store_id.id,
                    'product_id': l.item_id.product_id.id,
                    'item_id': l.item_id.id,
                    'quantity': abs(l.variance),
                    'unit_cost': l.item_id.unit_cost,
                    'note': _('تسوية جرد %s — %s') % (
                        c.name, _('زيادة') if gain else _('عجز')),
                })
            moves.action_done()
            c.state = 'done'
            c.message_post(body=_('✅ اعتُمد الجرد — دقة %.0f%%، %s بندًا بفروقات.')
                           % (c.accuracy, c.variance_lines))

    def action_cancel(self):
        self.write({'state': 'cancelled'})


class StockCountLine(models.Model):
    _name = 'care.cafm.stock.count.line'
    _description = 'بند جرد'
    _order = 'id'

    count_id = fields.Many2one('care.cafm.stock.count', required=True, ondelete='cascade',
                               index=True)
    item_id = fields.Many2one('care.cafm.stock.item', string='الصنف', required=True)
    product_id = fields.Many2one(related='item_id.product_id', string='المنتج', store=True)
    uom_name = fields.Char(related='item_id.uom_name', string='الوحدة')
    book_qty = fields.Float(string='الرصيد الدفتري', compute='_compute_book', store=True)
    counted_qty = fields.Float(string='العدد الفعلي')
    variance = fields.Float(string='الفرق', compute='_compute_variance', store=True)
    variance_value = fields.Float(string='قيمة الفرق', compute='_compute_variance', store=True)
    reason = fields.Selection([
        ('damage', 'تلف'), ('expiry', 'انتهاء صلاحية'), ('theft', 'فقد'),
        ('miscount', 'خطأ عدّ سابق'), ('unrecorded', 'صرف غير مسجّل'), ('other', 'أخرى'),
    ], string='سبب الفرق')
    note = fields.Char(string='ملاحظة')
    counted = fields.Boolean(string='تمّ عدّه', default=False,
                             help='بند لم يُعدّ بعد لا يُحتسب فرقًا ولا يُسوّى.')

    def write(self, vals):
        # Entering a figure IS the act of counting. Without this, a line
        # left untouched reads as zero on hand — a total loss — and
        # approving the sheet would wipe stock that is sitting on the shelf.
        if 'counted_qty' in vals and 'counted' not in vals:
            vals = dict(vals, counted=True)
        return super().write(vals)

    @api.depends('item_id.on_hand', 'count_id.state')
    def _compute_book(self):
        """The book figure is frozen the moment the count leaves draft.
        Otherwise approving the count rewrites the balance it was measured
        against, and every finished count reports itself as 100% accurate —
        erasing the discrepancy it existed to record."""
        for l in self:
            if l.count_id.state == 'draft':
                l.book_qty = l.item_id.on_hand
            elif not l.book_qty:
                l.book_qty = l.item_id.on_hand

    @api.depends('counted_qty', 'book_qty', 'counted', 'item_id.unit_cost')
    def _compute_variance(self):
        for l in self:
            if not l.counted:
                l.variance = l.variance_value = 0.0
                continue
            l.variance = (l.counted_qty or 0.0) - (l.book_qty or 0.0)
            l.variance_value = l.variance * (l.item_id.unit_cost or 0.0)


class StockRequest(models.Model):
    """A replenishment request. Separate from a purchase order because most of
    them are answered from another store, not from a supplier."""
    _name = 'care.cafm.stock.request'
    _description = 'طلب تعويض مخزون'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    store_id = fields.Many2one('care.cafm.store', string='المخزن الطالب', required=True,
                               tracking=True, index=True)
    facility_id = fields.Many2one(related='store_id.facility_id', store=True, index=True)
    source_store_id = fields.Many2one('care.cafm.store', string='المخزن المورِّد',
                                      tracking=True,
                                      help='اتركه فارغًا إن كان التوريد من مورّد خارجي.')
    requested_by = fields.Many2one('res.users', string='الطالب',
                                   default=lambda s: s.env.user, tracking=True)
    needed_by = fields.Date(string='مطلوب بحلول', tracking=True)
    urgency = fields.Selection([
        ('normal', 'عادي'), ('high', 'عاجل'), ('critical', 'حرج — توقّف عمل'),
    ], string='الأولوية', default='normal', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'مسودة'), ('submitted', 'مُرسَل'), ('approved', 'معتمد'),
        ('fulfilled', 'تم التوريد'), ('rejected', 'مرفوض'), ('cancelled', 'ملغى'),
    ], string='الحالة', default='draft', required=True, tracking=True)
    line_ids = fields.One2many('care.cafm.stock.request.line', 'request_id', string='الأصناف')
    reason = fields.Text(string='المبرّر')
    reject_reason = fields.Char(string='سبب الرفض')
    total_value = fields.Float(string='القيمة التقديرية', compute='_compute_total', store=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.cafm.stock.request') or '/'
        return super().create(vals_list)

    @api.depends('line_ids.quantity', 'line_ids.unit_cost')
    def _compute_total(self):
        for r in self:
            r.total_value = sum(l.quantity * (l.unit_cost or 0.0) for l in r.line_ids)

    def action_submit(self):
        for r in self:
            if not r.line_ids:
                raise UserError(_('أضف صنفًا واحدًا على الأقل.'))
            r.state = 'submitted'
            r._notify(_('📦 طلب تعويض مخزون جديد'), 'task')

    def action_approve(self):
        self.write({'state': 'approved'})
        for r in self:
            r._notify(_('✅ اعتُمد طلب التعويض'), 'info')

    def action_reject(self, reason=None):
        for r in self:
            r.write({'state': 'rejected', 'reject_reason': reason or r.reject_reason})

    def action_fulfil(self):
        """Move the goods. A request marked fulfilled without a move is a lie
        the balance will contradict later."""
        Move = self.env['care.cafm.stock.move'].sudo()
        for r in self:
            if r.state != 'approved':
                raise UserError(_('يُورَّد الطلب بعد اعتماده فقط.'))
            moves = Move.browse()
            for l in r.line_ids:
                moves |= Move.create({
                    'move_type': 'transfer' if r.source_store_id else 'receipt',
                    'store_id': (r.source_store_id or r.store_id).id,
                    'dest_store_id': r.store_id.id if r.source_store_id else False,
                    'product_id': l.product_id.id,
                    'quantity': l.quantity,
                    'unit_cost': l.unit_cost,
                    'note': _('تعويض بموجب %s') % r.name,
                })
            # A move sitting in draft has not changed any balance yet — confirm
            # it, or the request says "supplied" while the shelf says otherwise.
            moves.action_done()
            r.state = 'fulfilled'
            r._notify(_('📥 وصل التعويض المطلوب'), 'info')

    def _notify(self, title, kind):
        self.ensure_one()
        if 'care.cafm.notification' not in self.env:
            return
        users = self.env['res.users'].sudo().search(
            [('groups_id', 'in', self.env.ref('base.group_erp_manager').id)], limit=8)
        users |= self.requested_by
        try:
            self.env['care.cafm.notification'].sudo().push(
                users, title, '%s — %s' % (self.name, self.store_id.name or ''), ntype=kind)
        except Exception:
            pass

    @api.model
    def _cron_low_stock(self):
        """Raise a draft request for whatever fell below its minimum, and tell
        the keeper. A reorder point nobody watches is decoration."""
        Item = self.env['care.cafm.stock.item'].sudo()
        # low_stock is the boolean; to_reorder is the suggested QUANTITY,
        # so it must not be used as a flag in a domain.
        low = Item.search([('low_stock', '=', True)])
        by_store = {}
        for i in low:
            by_store.setdefault(i.store_id, []).append(i)
        made = 0
        for store, items in by_store.items():
            open_req = self.search([('store_id', '=', store.id),
                                    ('state', 'in', ('draft', 'submitted', 'approved'))], limit=1)
            if open_req:
                continue
            self.create({
                'store_id': store.id, 'urgency': 'high',
                'reason': _('تحت الحد الأدنى — أُنشئ تلقائيًا'),
                'line_ids': [(0, 0, {
                    'product_id': i.product_id.id,
                    'quantity': i.to_reorder or max(1.0, (i.max_qty or i.min_qty * 2) - i.on_hand),
                    'unit_cost': i.unit_cost,
                }) for i in items],
            })
            made += 1
        return made


class StockRequestLine(models.Model):
    _name = 'care.cafm.stock.request.line'
    _description = 'بند طلب تعويض'
    _order = 'id'

    request_id = fields.Many2one('care.cafm.stock.request', required=True, ondelete='cascade',
                                 index=True)
    product_id = fields.Many2one('product.product', string='المنتج', required=True)
    quantity = fields.Float(string='الكمية المطلوبة', default=1.0, required=True)
    uom_name = fields.Char(related='product_id.uom_id.name', string='الوحدة')
    unit_cost = fields.Float(string='تكلفة الوحدة')
    on_hand = fields.Float(string='الرصيد الحالي', compute='_compute_on_hand')
    note = fields.Char(string='ملاحظة')

    @api.depends('product_id', 'request_id.store_id')
    def _compute_on_hand(self):
        Item = self.env['care.cafm.stock.item'].sudo()
        for l in self:
            it = Item.search([('store_id', '=', l.request_id.store_id.id),
                              ('product_id', '=', l.product_id.id)], limit=1) \
                if (l.request_id.store_id and l.product_id) else None
            l.on_hand = it.on_hand if it else 0.0
