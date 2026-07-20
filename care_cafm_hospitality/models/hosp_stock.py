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
    _description = 'Hospitality Supply'
    _inherit = ['mail.thread']
    _order = 'category, name'

    name = fields.Char(string='Supply', required=True, translate=True, tracking=True)
    code = fields.Char(string='Code', tracking=True)
    category = fields.Selection([
        ('coffee', 'Coffee and Beans'), ('tea', 'Tea and Herbs'), ('sugar', 'Sugar and Sweeteners'),
        ('dairy', 'Dairy'), ('water', 'Water and Beverages'), ('food', 'Food'),
        ('disposable', 'Serving Supplies'), ('other', 'Other'),
    ], string='Category', default='other', required=True, tracking=True)
    uom_name = fields.Selection([
        ('g', 'Gram'), ('kg', 'Kilogram'), ('ml', 'Milliliter'), ('l', 'Liter'),
        ('pcs', 'Piece'),
    ], string='Unit of Measure', default='g', required=True, tracking=True,
        help='The base unit used to calculate balance and consumption.')
    pack_name = fields.Char(string='Package Name', default='Bag',
                            help='As purchased: bag, box, carton…')
    pack_size = fields.Float(string='Package Content', default=1000.0, required=True,
                             tracking=True,
                             help='In the unit of measure. Example: a 1000 gram bag of coffee.')
    on_hand = fields.Float(string='Balance', default=0.0, tracking=True,
                           help='In the base unit of measure.')
    packs_on_hand = fields.Float(string='Balance in Packages', compute='_compute_packs',
                                 store=True)
    min_qty = fields.Float(string='Reorder Threshold', default=0.0, tracking=True,
                           help='In the unit of measure.')
    unit_cost = fields.Float(string='Unit Cost', tracking=True,
                             help='Cost of a single unit (not the package).')
    pack_cost = fields.Float(string='Package Cost', compute='_compute_packs', store=True)
    stock_value = fields.Float(string='Balance Value', compute='_compute_packs', store=True)

    facility_id = fields.Many2one('care.cafm.facility', string='Facility',
                                  tracking=True, index=True)
    supplier_type = fields.Selection([
        ('care', 'From CARE'), ('external', 'External Supplier'),
    ], string='Supply Source', default='care', required=True, tracking=True,
        help='Sets the default when creating a purchase request for this supply.')
    partner_id = fields.Many2one('res.partner', string='External Supplier',
                                 tracking=True)

    recipe_ids = fields.One2many('care.hosp.recipe', 'supply_id', string='Used In')
    move_ids = fields.One2many('care.hosp.stock.move', 'supply_id', string='Moves')

    # ---- the numbers that make this legible -------------------------------
    servings_left = fields.Float(string='Enough For (Servings)', compute='_compute_cover',
                                 help='The lowest number of servings that can be made from the current balance.')
    per_serving_hint = fields.Char(string='Rate', compute='_compute_cover')
    daily_use = fields.Float(string='Average Daily Consumption', compute='_compute_cover')
    days_cover = fields.Float(string='Coverage (Days)', compute='_compute_cover')
    low_stock = fields.Boolean(string='Low', compute='_compute_flags', store=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [('code_uniq', 'unique(code, facility_id)',
                         'This supply code is already used in this facility.')]

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
                '%.4g %s / serving' % (biggest, dict(self._fields['uom_name'].selection).get(
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
    _description = 'Consumption Recipe'
    _order = 'item_id, id'

    item_id = fields.Many2one('care.hosp.item', string='Item', required=True,
                              ondelete='cascade', index=True)
    supply_id = fields.Many2one('care.hosp.supply', string='Supply', required=True,
                                ondelete='restrict', index=True)
    qty_per_serving = fields.Float(string='Quantity per Serving', required=True, default=1.0,
                                   help='In the supply unit of measure. Example: 18 grams of coffee for an espresso.')
    uom_name = fields.Selection(related='supply_id.uom_name', string='Unit')
    option_id = fields.Many2one(
        'care.hosp.option', string='Conditional on Option',
        help='Leave it empty to always count it. Set it to count only when this '
             'option is chosen — such as extra sugar.')
    servings_per_pack = fields.Float(string='Servings per Package', compute='_compute_yield',
                                     store=True,
                                     help='How many cups one bag or box yields.')
    cost_per_serving = fields.Float(string='Serving Cost', compute='_compute_yield',
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
                raise UserError(_('The quantity per serving must be greater than zero.'))


class HospStockMove(models.Model):
    """The pantry ledger. Positive adds, negative consumes."""
    _name = 'care.hosp.stock.move'
    _description = 'Hospitality Stock Move'
    _order = 'date desc, id desc'

    supply_id = fields.Many2one('care.hosp.supply', string='Supply', required=True,
                                ondelete='cascade', index=True)
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True,
                           index=True)
    move_type = fields.Selection([
        ('receipt', 'Receipt'), ('consume', 'Order Consumption'), ('waste', 'Waste/Damage'),
        ('adjust', 'Inventory Adjustment'), ('return', 'Return to Supplier'),
    ], string='Move Type', required=True, default='consume', index=True)
    quantity = fields.Float(string='Quantity', required=True,
                            help='Positive to add, negative to deduct.')
    order_id = fields.Many2one('care.hosp.order', string='Order', ondelete='set null',
                               index=True)
    purchase_id = fields.Many2one('care.hosp.purchase', string='Purchase Request',
                                  ondelete='set null')
    user_id = fields.Many2one('res.users', string='By', default=lambda s: s.env.user)
    note = fields.Char(string='Note')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)


class HospPurchase(models.Model):
    """Buying the pantry back up, from CARE's own store or from outside.

    Either way it ends as a receipt in the same ledger — the balance must not
    depend on who supplied it.
    """
    _name = 'care.hosp.purchase'
    _description = 'Hospitality Purchase Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    facility_id = fields.Many2one('care.cafm.facility', string='Facility', required=True,
                                  tracking=True, index=True)
    date = fields.Date(string='Date', default=fields.Date.context_today,
                       required=True, tracking=True)
    source = fields.Selection([
        ('care', 'From CARE'), ('external', 'External Supplier'),
    ], string='Purchase Source', default='care', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Supplier',
                                 tracking=True,
                                 help='Required when purchasing from an external supplier.')
    reference = fields.Char(string='Invoice/Order Number', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Sent'), ('approved', 'Approved'),
        ('received', 'Received'), ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    line_ids = fields.One2many('care.hosp.purchase.line', 'purchase_id', string='Lines')
    total_cost = fields.Float(string='Total', compute='_compute_total', store=True)
    note = fields.Text(string='Notes')
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
                raise UserError(_('Set the external supplier.'))

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_receive(self):
        """Receiving is what changes the balance — not approving, and not the
        arrival of an invoice."""
        for p in self:
            if p.state not in ('approved', 'submitted'):
                raise UserError(_('The request is received after it is approved.'))
            if not p.line_ids:
                raise UserError(_('There are no lines in the request.'))
            for l in p.line_ids:
                qty = l.quantity * (l.supply_id.pack_size or 1.0) if l.by_pack \
                    else l.quantity
                l.supply_id._apply(
                    qty, 'receipt',
                    note=_('Receipt under %s (%s)') % (
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
                'note': _('Created automatically: supplies below the threshold or with less than a week of coverage.'),
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
    _description = 'Hospitality Purchase Line'
    _order = 'id'

    purchase_id = fields.Many2one('care.hosp.purchase', required=True,
                                  ondelete='cascade', index=True)
    supply_id = fields.Many2one('care.hosp.supply', string='Supply', required=True)
    by_pack = fields.Boolean(string='By Package', default=True,
                             help='Purchasing is usually done in packages, while the balance is calculated in units.')
    quantity = fields.Float(string='Quantity', default=1.0, required=True)
    uom_label = fields.Char(string='Unit', compute='_compute_labels')
    unit_cost = fields.Float(string='Unit Cost')
    subtotal = fields.Float(string='Total', compute='_compute_labels', store=True)
    base_qty = fields.Float(string='Quantity in Base Unit', compute='_compute_labels',
                            store=True)

    @api.depends('quantity', 'by_pack', 'unit_cost', 'supply_id.pack_size',
                 'supply_id.pack_name', 'supply_id.uom_name')
    def _compute_labels(self):
        uom = dict(self.env['care.hosp.supply']._fields['uom_name'].selection)
        for l in self:
            size = l.supply_id.pack_size or 1.0
            l.base_qty = l.quantity * size if l.by_pack else l.quantity
            l.uom_label = (l.supply_id.pack_name or 'Package') if l.by_pack \
                else uom.get(l.supply_id.uom_name, '')
            l.subtotal = l.base_qty * (l.unit_cost or l.supply_id.unit_cost or 0.0)
