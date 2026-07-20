# -*- coding: utf-8 -*-
"""Hospitality stock, counted in the unit people actually buy and consume.

A pantry does not run out of "0.4 kg of coffee" — it runs out of cups. The
storekeeper buys a 1 kg bag, the barista pulls 18 g per espresso, and the
question everyone actually asks is "how many more cups can we serve, and when
do I reorder?". So the yield is the centre of this model: every item declares
what it consumes per serving, and every balance is reported both in its own
unit and in servings.

That one number also makes waste visible. The recipes say what *should* have
been used for the orders delivered; a physical count says what is really left.
The gap is spillage, over-pouring, or something walking out of the pantry —
and until it is computed nobody can see it.
"""
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HospSupply(models.Model):
    """One consumable behind the menu: beans, sugar, milk, cups, lids."""
    _name = 'care.hosp.supply'
    _description = 'مستهلك ضيافة'
    _inherit = ['mail.thread']
    _order = 'category, name'

    name = fields.Char(string='المستهلك', required=True, translate=True, tracking=True)
    code = fields.Char(string='الرمز', tracking=True)
    category = fields.Selection([
        ('coffee', 'بنّ وقهوة'), ('tea', 'شاي وأعشاب'), ('sugar', 'سكر ومحليات'),
        ('dairy', 'ألبان'), ('water', 'مياه ومشروبات'), ('food', 'مأكولات'),
        ('disposable', 'مستلزمات تقديم'), ('other', 'أخرى'),
    ], string='الفئة', default='other', required=True, tracking=True)
    uom_name = fields.Selection([
        ('g', 'جرام'), ('kg', 'كيلوجرام'), ('ml', 'مليلتر'), ('l', 'لتر'),
        ('pcs', 'قطعة'),
    ], string='وحدة القياس', default='g', required=True, tracking=True,
        help='الوحدة الأساسية التي يُحسب بها الرصيد والاستهلاك.')
    pack_name = fields.Char(string='اسم العبوة', default='كيس',
                            help='كما تُشترى: كيس، علبة، كرتون…')
    pack_size = fields.Float(string='محتوى العبوة', default=1000.0, required=True,
                             tracking=True,
                             help='بوحدة القياس. مثال: كيس بنّ 1000 جرام.')
    on_hand = fields.Float(string='الرصيد', default=0.0, tracking=True,
                           help='بوحدة القياس الأساسية.')
    packs_on_hand = fields.Float(string='الرصيد بالعبوات', compute='_compute_packs',
                                 store=True)
    min_qty = fields.Float(string='حد إعادة الطلب', default=0.0, tracking=True,
                           help='بوحدة القياس.')
    unit_cost = fields.Float(string='تكلفة الوحدة', tracking=True,
                             help='تكلفة الوحدة الواحدة (لا العبوة).')
    pack_cost = fields.Float(string='تكلفة العبوة', compute='_compute_packs', store=True)
    stock_value = fields.Float(string='قيمة الرصيد', compute='_compute_packs', store=True)

    facility_id = fields.Many2one('care.cafm.facility', string='المرفق',
                                  tracking=True, index=True)
    supplier_type = fields.Selection([
        ('care', 'من شركة CARE'), ('external', 'مورّد خارجي'),
    ], string='مصدر التوريد', default='care', required=True, tracking=True,
        help='يحدّد الافتراضي عند إنشاء طلب شراء لهذا الصنف.')
    partner_id = fields.Many2one('res.partner', string='المورّد الخارجي',
                                 tracking=True)

    recipe_ids = fields.One2many('care.hosp.recipe', 'supply_id', string='يدخل في')
    move_ids = fields.One2many('care.hosp.stock.move', 'supply_id', string='الحركات')

    # ---- the numbers that make this legible -------------------------------
    servings_left = fields.Float(string='يكفي (حصص)', compute='_compute_cover',
                                 help='أقل عدد حصص يمكن تقديمها من الرصيد الحالي.')
    per_serving_hint = fields.Char(string='المعدّل', compute='_compute_cover')
    daily_use = fields.Float(string='متوسط الاستهلاك اليومي', compute='_compute_cover')
    days_cover = fields.Float(string='تغطية (يوم)', compute='_compute_cover')
    low_stock = fields.Boolean(string='منخفض', compute='_compute_flags', store=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [('code_uniq', 'unique(code, facility_id)',
                         'رمز المستهلك مستخدم في هذا المرفق.')]

    @api.depends('on_hand', 'pack_size', 'unit_cost')
    def _compute_packs(self):
        for s in self:
            size = s.pack_size or 1.0
            s.packs_on_hand = (s.on_hand or 0.0) / size
            s.pack_cost = (s.unit_cost or 0.0) * size
            s.stock_value = (s.on_hand or 0.0) * (s.unit_cost or 0.0)

    @api.depends('on_hand', 'min_qty')
    def _compute_flags(self):
        for s in self:
            s.low_stock = bool(s.min_qty) and s.on_hand <= s.min_qty

    def _compute_cover(self):
        """Servings left, and how long that lasts at the current rate.

        Reporting 400 g of coffee tells a storekeeper nothing. Reporting
        "22 espressos, about 3 days" is a decision.
        """
        since = fields.Datetime.now() - timedelta(days=30)
        Move = self.env['care.hosp.stock.move'].sudo()
        for s in self:
            per = min(s.recipe_ids.mapped('qty_per_serving') or [0.0]) or 0.0
            biggest = max(s.recipe_ids.mapped('qty_per_serving') or [0.0]) or 0.0
            s.servings_left = (s.on_hand / biggest) if biggest else 0.0
            s.per_serving_hint = (
                '%.4g %s / حصة' % (biggest, dict(self._fields['uom_name'].selection).get(
                    s.uom_name, ''))) if biggest else ''
            used = sum(abs(m.quantity) for m in Move.search([
                ('supply_id', '=', s.id), ('move_type', '=', 'consume'),
                ('date', '>=', since)]))
            s.daily_use = used / 30.0 if used else 0.0
            s.days_cover = (s.on_hand / s.daily_use) if s.daily_use else 0.0

    def name_get(self):
        uom = dict(self._fields['uom_name'].selection)
        return [(s.id, '%s (%s)' % (s.name, uom.get(s.uom_name, ''))) for s in self]

    def _apply(self, qty, move_type, note=None, order=None):
        """Every change to a balance goes through the ledger, so the pantry can
        always explain how it got where it is."""
        self.ensure_one()
        self.env['care.hosp.stock.move'].sudo().create({
            'supply_id': self.id, 'quantity': qty, 'move_type': move_type,
            'note': note or '', 'order_id': order.id if order else False,
        })
        self.sudo().on_hand = (self.on_hand or 0.0) + qty
        return True


class HospRecipe(models.Model):
    """What one serving of an item consumes. This is the formula.

    Kept as its own model rather than a field on the item because a drink
    consumes several things — beans, a cup, a lid, milk — and each has its own
    rate.
    """
    _name = 'care.hosp.recipe'
    _description = 'معادلة استهلاك'
    _order = 'item_id, id'

    item_id = fields.Many2one('care.hosp.item', string='الصنف', required=True,
                              ondelete='cascade', index=True)
    supply_id = fields.Many2one('care.hosp.supply', string='المستهلك', required=True,
                                ondelete='restrict', index=True)
    qty_per_serving = fields.Float(string='الكمية لكل حصة', required=True, default=1.0,
                                   help='بوحدة قياس المستهلك. مثال: 18 جرام بنّ للإسبريسو.')
    uom_name = fields.Selection(related='supply_id.uom_name', string='الوحدة')
    option_id = fields.Many2one(
        'care.hosp.option', string='مشروط بالخيار',
        help='اتركه فارغًا ليُحتسب دائمًا. حدّده ليُحتسب فقط عند اختيار هذا '
             'الخيار — مثل «سكر زيادة».')
    servings_per_pack = fields.Float(string='الحصص لكل عبوة', compute='_compute_yield',
                                     store=True,
                                     help='كم كوبًا يعطيه الكيس/العلبة الواحدة.')
    cost_per_serving = fields.Float(string='تكلفة الحصة', compute='_compute_yield',
                                    store=True)

    @api.depends('qty_per_serving', 'supply_id.pack_size', 'supply_id.unit_cost')
    def _compute_yield(self):
        """The answer to 'how many cups per kilo'."""
        for r in self:
            q = r.qty_per_serving or 0.0
            r.servings_per_pack = ((r.supply_id.pack_size or 0.0) / q) if q else 0.0
            r.cost_per_serving = q * (r.supply_id.unit_cost or 0.0)

    @api.constrains('qty_per_serving')
    def _check_qty(self):
        for r in self:
            if r.qty_per_serving <= 0:
                raise UserError(_('الكمية لكل حصة يجب أن تكون أكبر من صفر.'))


class HospStockMove(models.Model):
    """The pantry ledger. Positive adds, negative consumes."""
    _name = 'care.hosp.stock.move'
    _description = 'حركة مخزون ضيافة'
    _order = 'date desc, id desc'

    supply_id = fields.Many2one('care.hosp.supply', string='المستهلك', required=True,
                                ondelete='cascade', index=True)
    date = fields.Datetime(string='التاريخ', default=fields.Datetime.now, required=True,
                           index=True)
    move_type = fields.Selection([
        ('receipt', 'توريد'), ('consume', 'استهلاك بطلب'), ('waste', 'هدر/تلف'),
        ('adjust', 'تسوية جرد'), ('return', 'إرجاع للمورّد'),
    ], string='نوع الحركة', required=True, default='consume', index=True)
    quantity = fields.Float(string='الكمية', required=True,
                            help='موجبة للإضافة، سالبة للخصم.')
    order_id = fields.Many2one('care.hosp.order', string='الطلب', ondelete='set null',
                               index=True)
    purchase_id = fields.Many2one('care.hosp.purchase', string='طلب الشراء',
                                  ondelete='set null')
    user_id = fields.Many2one('res.users', string='بواسطة', default=lambda s: s.env.user)
    note = fields.Char(string='ملاحظة')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)


class HospPurchase(models.Model):
    """Buying the pantry back up, from CARE's own store or from outside.

    Either way it ends as a receipt in the same ledger — the balance must not
    depend on who supplied it.
    """
    _name = 'care.hosp.purchase'
    _description = 'طلب شراء ضيافة'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True,
                                  tracking=True, index=True)
    date = fields.Date(string='التاريخ', default=fields.Date.context_today,
                       required=True, tracking=True)
    source = fields.Selection([
        ('care', 'من شركة CARE'), ('external', 'مورّد خارجي'),
    ], string='مصدر الشراء', default='care', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='المورّد',
                                 tracking=True,
                                 help='مطلوب عند الشراء من مورّد خارجي.')
    reference = fields.Char(string='رقم الفاتورة/الأمر', tracking=True)
    state = fields.Selection([
        ('draft', 'مسودة'), ('submitted', 'مُرسَل'), ('approved', 'معتمد'),
        ('received', 'تم الاستلام'), ('cancelled', 'ملغى'),
    ], string='الحالة', default='draft', required=True, tracking=True)
    line_ids = fields.One2many('care.hosp.purchase.line', 'purchase_id', string='البنود')
    total_cost = fields.Float(string='الإجمالي', compute='_compute_total', store=True)
    note = fields.Text(string='ملاحظات')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'care.hosp.purchase') or '/'
        return super().create(vals_list)

    @api.depends('line_ids.subtotal')
    def _compute_total(self):
        for p in self:
            p.total_cost = sum(p.line_ids.mapped('subtotal'))

    @api.constrains('source', 'partner_id')
    def _check_partner(self):
        for p in self:
            if p.source == 'external' and not p.partner_id:
                raise UserError(_('حدّد المورّد الخارجي.'))

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_receive(self):
        """Receiving is what changes the balance — not approving, and not the
        arrival of an invoice."""
        for p in self:
            if p.state not in ('approved', 'submitted'):
                raise UserError(_('يُستلم الطلب بعد اعتماده.'))
            if not p.line_ids:
                raise UserError(_('لا توجد بنود في الطلب.'))
            for l in p.line_ids:
                qty = l.quantity * (l.supply_id.pack_size or 1.0) if l.by_pack \
                    else l.quantity
                l.supply_id._apply(
                    qty, 'receipt',
                    note=_('توريد بموجب %s (%s)') % (
                        p.name, dict(self._fields['source'].selection)[p.source]))
                if l.unit_cost:
                    l.supply_id.sudo().unit_cost = l.unit_cost
            p.state = 'received'

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    @api.model
    def _cron_low_supplies(self):
        """Raise a draft purchase per facility for whatever will not last.

        Coverage in days, not just a minimum quantity: a pantry with 2 kg of
        coffee is fine in an office and empty by Tuesday in a hospital lobby.
        """
        Supply = self.env['care.hosp.supply'].sudo()
        low = Supply.search([('active', '=', True)]).filtered(
            lambda s: s.low_stock or (s.days_cover and s.days_cover < 7))
        made = 0
        by_fac = {}
        for s in low:
            by_fac.setdefault(s.facility_id, []).append(s)
        for fac, sups in by_fac.items():
            if not fac:
                continue
            if self.search_count([('facility_id', '=', fac.id),
                                  ('state', 'in', ('draft', 'submitted', 'approved'))]):
                continue
            self.create({
                'facility_id': fac.id,
                'source': sups[0].supplier_type,
                'partner_id': sups[0].partner_id.id or False,
                'note': _('أُنشئ تلقائيًا: أصناف تحت الحد أو تغطيتها أقل من أسبوع.'),
                'line_ids': [(0, 0, {
                    'supply_id': s.id, 'by_pack': True,
                    'quantity': max(1.0, round(
                        ((s.min_qty * 2) - s.on_hand) / (s.pack_size or 1.0), 0)),
                    'unit_cost': s.unit_cost,
                }) for s in sups],
            })
            made += 1
        return made


class HospPurchaseLine(models.Model):
    _name = 'care.hosp.purchase.line'
    _description = 'بند شراء ضيافة'
    _order = 'id'

    purchase_id = fields.Many2one('care.hosp.purchase', required=True,
                                  ondelete='cascade', index=True)
    supply_id = fields.Many2one('care.hosp.supply', string='المستهلك', required=True)
    by_pack = fields.Boolean(string='بالعبوة', default=True,
                             help='الشراء يتم بالعبوات عادةً، والرصيد يُحسب بالوحدات.')
    quantity = fields.Float(string='الكمية', default=1.0, required=True)
    uom_label = fields.Char(string='الوحدة', compute='_compute_labels')
    unit_cost = fields.Float(string='تكلفة الوحدة')
    subtotal = fields.Float(string='الإجمالي', compute='_compute_labels', store=True)
    base_qty = fields.Float(string='الكمية بالوحدة الأساسية', compute='_compute_labels',
                            store=True)

    @api.depends('quantity', 'by_pack', 'unit_cost', 'supply_id.pack_size',
                 'supply_id.pack_name', 'supply_id.uom_name')
    def _compute_labels(self):
        uom = dict(self.env['care.hosp.supply']._fields['uom_name'].selection)
        for l in self:
            size = l.supply_id.pack_size or 1.0
            l.base_qty = l.quantity * size if l.by_pack else l.quantity
            l.uom_label = (l.supply_id.pack_name or 'عبوة') if l.by_pack \
                else uom.get(l.supply_id.uom_name, '')
            l.subtotal = l.base_qty * (l.unit_cost or l.supply_id.unit_cost or 0.0)
