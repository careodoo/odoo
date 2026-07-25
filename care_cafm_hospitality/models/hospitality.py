# -*- coding: utf-8 -*-
"""Hospitality (خدمة الضيافة) — office catering as a CAFM service.

The shape of the problem: staff order a drink from their desk, a kitchen crew
prepares it against a clock, and the client wants to know who consumed what and
to cap it. So the model is a small ordering system with three distinct audiences
— the requester, the kitchen station, and the client's finance/admin — and each
gets the data in the form it actually needs.

Ordering is per-line rather than per-order at the kitchen: one order can hold a
coffee and a tea that different stations prepare and bump independently.
"""
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HospCategory(models.Model):
    _name = 'care.hosp.category'
    _description = 'Hospitality Category'
    _order = 'sequence, name'

    name = fields.Char(string='Category', required=True, translate=True)
    code = fields.Char(string='Code')
    icon = fields.Char(string='Icon', default='☕')
    color = fields.Char(string='Color', default='#8a6d3b',
                        help='Category color in the portal and on the kitchen display.')
    sequence = fields.Integer(default=10)
    description = fields.Text(string='Description', translate=True)
    item_ids = fields.One2many('care.hosp.item', 'category_id', string='Items')
    item_count = fields.Integer(compute='_compute_item_count', string='Item Count')
    active = fields.Boolean(default=True)

    def _compute_item_count(self):
        data = self.env['care.hosp.item']._read_group(
            [('category_id', 'in', self.ids)], ['category_id'], ['__count'])
        counts = {c.id: n for c, n in data}
        for r in self:
            r.item_count = counts.get(r.id, 0)


class HospOptionGroup(models.Model):
    """A question asked about an item — "كم سكر؟", "الحجم؟". Reusable across
    items so "السكر" is defined once and attached to every hot drink."""
    _name = 'care.hosp.option.group'
    _description = 'Option Group'
    _order = 'sequence, name'

    name = fields.Char(string='Group', required=True, translate=True)
    sequence = fields.Integer(default=10)
    required = fields.Boolean(string='Required', default=True,
                              help='The requester must choose before completing the order.')
    multi = fields.Boolean(string='Multiple Choice',
                           help='Like add-ons: more than one option can be chosen.')
    max_select = fields.Integer(string='Max Choices', default=1)
    option_ids = fields.One2many('care.hosp.option', 'group_id', string='Options')
    active = fields.Boolean(default=True)


class HospOption(models.Model):
    _name = 'care.hosp.option'
    _description = 'Option'
    _order = 'sequence, name'

    name = fields.Char(string='Option', required=True, translate=True)
    group_id = fields.Many2one('care.hosp.option.group', string='Group',
                               required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    is_default = fields.Boolean(string='Default')
    extra_cost = fields.Float(string='Extra Cost', default=0.0)
    active = fields.Boolean(default=True)


class HospStation(models.Model):
    """Where an item is actually made. Splitting the kitchen into stations keeps
    the barista's screen free of sandwich orders."""
    _name = 'care.hosp.station'
    _description = 'Preparation Station'
    _order = 'name'

    name = fields.Char(string='Station', required=True, translate=True)
    facility_id = fields.Many2one('care.cafm.facility', string='Facility', required=True)
    icon = fields.Char(string='Icon', default='🍳')
    member_ids = fields.Many2many('hr.employee', string='Station Staff')
    open_from = fields.Float(string='Work Starts', default=7.0)
    open_to = fields.Float(string='Work Ends', default=17.0)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)


class HospItem(models.Model):
    _name = 'care.hosp.item'
    _description = 'Hospitality Item'
    _order = 'sequence, name'

    name = fields.Char(string='Item', required=True, translate=True)
    code = fields.Char(string='Code')
    category_id = fields.Many2one('care.hosp.category', string='Category', required=True)
    station_id = fields.Many2one('care.hosp.station', string='Preparation Station')
    sequence = fields.Integer(default=10)
    icon = fields.Char(string='Icon', default='☕')
    image = fields.Image(string='Image', max_width=512, max_height=512)
    description = fields.Text(string='Description', translate=True)
    option_group_ids = fields.Many2many('care.hosp.option.group', string='Option Groups')
    prep_minutes = fields.Integer(string='Preparation Time (Minutes)', default=5,
                                  help='Used as the target on the kitchen display.')
    unit_cost = fields.Float(string='Unit Cost',
                             help='For internal costing and consumption reports — it is not charged to the employee.')
    facility_ids = fields.Many2many('care.cafm.facility', string='Available in Facilities',
                                    help='Leave it empty to make it available in all facilities.')
    available = fields.Boolean(string='Available', default=True)
    unavailable_note = fields.Char(string='Unavailability Reason')
    serve_from = fields.Float(string='Served From', default=0.0)
    serve_to = fields.Float(string='Until', default=24.0)
    is_hot = fields.Boolean(string='Hot Drink')
    order_count = fields.Integer(compute='_compute_stats', string='Times Ordered')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def _compute_stats(self):
        data = self.env['care.hosp.order.line']._read_group(
            [('item_id', 'in', self.ids)], ['item_id'], ['quantity:sum'])
        counts = {i.id: q for i, q in data}
        for r in self:
            r.order_count = int(counts.get(r.id, 0))

    def is_servable_now(self):
        """Availability is a time window as well as a flag — breakfast items
        should stop being orderable at 11, not just be marked unavailable."""
        self.ensure_one()
        if not self.available:
            return False
        now = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        h = now.hour + now.minute / 60.0
        if self.serve_from or self.serve_to != 24.0:
            return self.serve_from <= h <= self.serve_to
        return True


class HospOrder(models.Model):
    _name = 'care.hosp.order'
    _description = 'Hospitality Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Order Number', default='/', copy=False, readonly=True, index=True)
    requester_id = fields.Many2one('res.users', string='Requester', required=True,
                                   default=lambda s: s.env.user, tracking=True, index=True)
    partner_id = fields.Many2one('res.partner', string='Entity', related='requester_id.partner_id',
                                 store=True, index=True)
    department_id = fields.Many2one('hr.department', string='Department', tracking=True, index=True,
                                    help='To charge the consumption to the cost center.')
    facility_id = fields.Many2one('care.cafm.facility', string='Facility', required=True, index=True)
    location_id = fields.Many2one('care.cafm.location', string='Location/Office')
    room_label = fields.Char(string='Office/Hall',
                             help='Free text for when the location is not registered as a place in the system.')

    line_ids = fields.One2many('care.hosp.order.line', 'order_id', string='Items')
    note = fields.Text(string='Notes')

    # guests / meetings — a very different order from "قهوتي الصباحية"
    order_type = fields.Selection([
        ('self', 'Personal Order'), ('meeting', 'Meeting'), ('guest', 'Visitor Hospitality'),
    ], string='Order Type', default='self', required=True, tracking=True)
    guest_count = fields.Integer(string='Attendee Count', default=1)
    guest_name = fields.Char(string='Guest/Entity Name')
    is_vip = fields.Boolean(string='VIP Hospitality', tracking=True)

    scheduled_at = fields.Datetime(string='Scheduled Serving Time',
                                   help='Leave it empty to prepare immediately.')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('await_approval', 'Awaiting Approval'),
        ('placed', 'Sent'),
        ('accepted', 'Accepted'),
        ('preparing', 'In Preparation'),
        ('ready', 'Ready'),
        ('delivered', 'Served'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True, index=True)

    placed_at = fields.Datetime(string='Submission Time', readonly=True, index=True)
    accepted_at = fields.Datetime(string='Acceptance Time', readonly=True)
    ready_at = fields.Datetime(string='Ready Time', readonly=True)
    delivered_at = fields.Datetime(string='Serving Time', readonly=True, index=True)
    prep_target = fields.Integer(string='Target (Minutes)', compute='_compute_target', store=True)
    prep_minutes = fields.Float(string='Actual Preparation Time', compute='_compute_times', store=True)
    wait_minutes = fields.Float(string='Total Waiting Time', compute='_compute_times', store=True)
    is_late = fields.Boolean(string='Late', compute='_compute_times', store=True, index=True)

    item_count = fields.Integer(string='Item Count', compute='_compute_totals', store=True)
    total_cost = fields.Float(string='Cost', compute='_compute_totals', store=True)

    rating = fields.Selection([('1', '★'), ('2', '★★'), ('3', '★★★'),
                               ('4', '★★★★'), ('5', '★★★★★')], string='Rating')
    rating_note = fields.Char(string='Rating Note')

    prepared_by = fields.Many2one('hr.employee', string='Prepared By', tracking=True)
    delivered_by = fields.Many2one('hr.employee', string='Served By')
    supplies_consumed = fields.Boolean(
        string='Deducted from Stock', default=False, copy=False, readonly=True,
        help='Prevents deducting the same order twice when it is delivered again.')
    reject_reason = fields.Char(string='Rejection Reason')
    approver_id = fields.Many2one('res.users', string='Approver')
    limit_note = fields.Char(string='Limit Note', readonly=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    # ---- computes ----
    @api.depends('line_ids.item_id.prep_minutes')
    def _compute_target(self):
        for o in self:
            # the order is ready when its slowest item is — they are made in parallel
            o.prep_target = max(o.line_ids.mapped('item_id.prep_minutes') or [5])

    @api.depends('placed_at', 'accepted_at', 'ready_at', 'delivered_at', 'state', 'prep_target')
    def _compute_times(self):
        now = fields.Datetime.now()
        for o in self:
            start = o.accepted_at or o.placed_at
            end = o.ready_at or (now if o.state in ('accepted', 'preparing') else False)
            o.prep_minutes = (end - start).total_seconds() / 60.0 if (start and end) else 0.0
            fin = o.delivered_at or (now if o.state not in ('delivered', 'cancelled', 'rejected') else False)
            o.wait_minutes = (fin - o.placed_at).total_seconds() / 60.0 if (o.placed_at and fin) else 0.0
            o.is_late = bool(o.state in ('placed', 'accepted', 'preparing')
                             and o.wait_minutes > (o.prep_target or 5))

    @api.depends('line_ids.quantity', 'line_ids.line_cost')
    def _compute_totals(self):
        for o in self:
            o.item_count = int(sum(o.line_ids.mapped('quantity')))
            o.total_cost = sum(o.line_ids.mapped('line_cost'))

    # ---- lifecycle ----
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.hosp.order') or '/'
        return super().create(vals_list)

    def action_place(self):
        """Submit to the kitchen — unless the requester is over their cap, in
        which case the order waits for a human instead of being thrown away."""
        for o in self:
            if not o.line_ids:
                raise UserError(_('Add at least one item.'))
            o._check_options()
            verdict = self.env['care.hosp.limit'].check_order(o)
            if verdict.get('blocked'):
                raise UserError(verdict['message'])
            if verdict.get('needs_approval'):
                o.write({'state': 'await_approval', 'limit_note': verdict['message']})
                o._notify_approvers(verdict['message'])
                continue
            o.write({'state': 'placed', 'placed_at': fields.Datetime.now()})
            o._notify_station()
        return True

    def action_approve(self):
        for o in self.filtered(lambda x: x.state == 'await_approval'):
            o.write({'state': 'placed', 'placed_at': fields.Datetime.now(),
                     'approver_id': self.env.user.id})
            o._notify_station()
            o._notify_requester(_('✅ Hospitality order approved'), o.name)
        return True

    def action_accept(self):
        emp = self.env.user.employee_id
        for o in self.filtered(lambda x: x.state == 'placed'):
            o.write({'state': 'accepted', 'accepted_at': fields.Datetime.now(),
                     'prepared_by': emp.id if emp else False})
            o._notify_requester(_('👨‍🍳 Your order is being prepared'), o.name)
        return True

    def action_preparing(self):
        self.filtered(lambda x: x.state in ('placed', 'accepted')).write({'state': 'preparing'})
        return True

    def action_ready(self):
        for o in self.filtered(lambda x: x.state in ('placed', 'accepted', 'preparing')):
            o.write({'state': 'ready', 'ready_at': fields.Datetime.now()})
            o.line_ids.write({'state': 'ready'})
            o._notify_requester(_('🔔 Your order is ready'), o.name)
        return True

    def action_deliver(self):
        emp = self.env.user.employee_id
        for o in self.filtered(lambda x: x.state in ('ready', 'preparing', 'accepted')):
            o.write({'state': 'delivered', 'delivered_at': fields.Datetime.now(),
                     'delivered_by': emp.id if emp else o.delivered_by.id})
            o.line_ids.write({'state': 'served'})
            o._consume_supplies()
        return True

    def _consume_supplies(self):
        """Deduct what this order actually used, once, on delivery.

        Delivery is the honest moment: an order cancelled while brewing has
        still consumed the beans, but one rejected before it starts has not,
        and deducting at order time would drain the pantry on paper for drinks
        nobody ever received.

        Options carry their own consumption — 'extra sugar' is three sachets,
        not the same as 'no sugar' — so a recipe line tied to an option only
        counts when that option was chosen.
        """
        Recipe = self.env['care.hosp.recipe'].sudo()
        for o in self:
            if o.supplies_consumed:
                continue
            for line in o.line_ids:
                chosen = set(line.option_ids.ids)
                for r in Recipe.search([('item_id', '=', line.item_id.id)]):
                    if r.option_id and r.option_id.id not in chosen:
                        continue
                    qty = (r.qty_per_serving or 0.0) * (line.quantity or 1.0)
                    if qty:
                        r.supply_id._apply(
                            -qty, 'consume',
                            note=_('Consumption %s × %s') % (line.item_id.name, line.quantity),
                            order=o)
            o.supplies_consumed = True
        return True

    def action_reject(self, reason=None):
        for o in self:
            o.write({'state': 'rejected', 'reject_reason': reason or o.reject_reason})
            o._notify_requester(_('⛔ Your order could not be completed'),
                                o.reject_reason or o.name)
        return True

    def action_cancel(self):
        self.filtered(lambda x: x.state not in ('delivered',)).write({'state': 'cancelled'})
        return True

    def action_reset(self):
        self.write({'state': 'draft'})
        return True

    def _check_options(self):
        """A required option group left unanswered means the kitchen has to
        guess — reject it at the door instead."""
        for o in self:
            for line in o.line_ids:
                for grp in line.item_id.option_group_ids.filtered('required'):
                    if not (line.option_ids & grp.option_ids):
                        raise UserError(_('Choose "%s" for the item "%s".') % (grp.name, line.item_id.name))

    # ---- notifications ----
    def _push(self, users, title, body):
        users = users.filtered('active')
        if not users or 'care.cafm.notification' not in self.env:
            return
        try:
            self.env['care.cafm.notification'].sudo().push(
                users, title, body, ntype='task', action_url='/hosp/order/%s' % self.id, record=self)
        except Exception:
            pass

    def _notify_requester(self, title, body):
        self._push(self.requester_id, title, body)

    def _notify_station(self):
        """Whoever mans the stations this order touches gets told at once."""
        emps = self.line_ids.mapped('item_id.station_id.member_ids')
        users = emps.mapped('user_id')
        self._push(users, _('🆕 New hospitality order'),
                   '%s — %s' % (self.name, self.room_label or self.location_id.name or ''))

    def _notify_approvers(self, message):
        approvers = self.env['care.hosp.limit'].approvers_for(self)
        self._push(approvers, _('🔐 Hospitality order needs your approval'),
                   '%s — %s' % (self.requester_id.name, message))


class HospOrderLine(models.Model):
    _name = 'care.hosp.order.line'
    _description = 'Hospitality Order Line'
    _order = 'id'

    order_id = fields.Many2one('care.hosp.order', string='Order', required=True,
                               ondelete='cascade', index=True)
    item_id = fields.Many2one('care.hosp.item', string='Item', required=True)
    category_id = fields.Many2one(related='item_id.category_id', store=True, string='Category')
    station_id = fields.Many2one(related='item_id.station_id', store=True, string='Station', index=True)
    quantity = fields.Float(string='Quantity', default=1.0, required=True)
    option_ids = fields.Many2many('care.hosp.option', string='Options')
    option_label = fields.Char(string='Specifications', compute='_compute_label', store=True)
    note = fields.Char(string='Note', help='Example: no foam, paper cup.')
    line_cost = fields.Float(string='Cost', compute='_compute_cost', store=True)
    state = fields.Selection([('queued', 'In Queue'), ('ready', 'Ready'), ('served', 'Served')],
                             string='Line Status', default='queued')
    # denormalised for the analytics screens — they group by these constantly
    requester_id = fields.Many2one(related='order_id.requester_id', store=True, index=True)
    department_id = fields.Many2one(related='order_id.department_id', store=True, index=True)
    facility_id = fields.Many2one(related='order_id.facility_id', store=True, index=True)
    order_state = fields.Selection(related='order_id.state', store=True, index=True)
    delivered_at = fields.Datetime(related='order_id.delivered_at', store=True, index=True)

    @api.depends('option_ids')
    def _compute_label(self):
        for l in self:
            l.option_label = ' · '.join(l.option_ids.mapped('name'))

    @api.depends('quantity', 'item_id.unit_cost', 'option_ids.extra_cost')
    def _compute_cost(self):
        for l in self:
            extra = sum(l.option_ids.mapped('extra_cost'))
            l.line_cost = (l.item_id.unit_cost + extra) * (l.quantity or 0)

    @api.constrains('quantity')
    def _check_qty(self):
        for l in self:
            if l.quantity <= 0:
                raise ValidationError(_('The quantity must be greater than zero.'))


class HospLimit(models.Model):
    """Consumption caps, set by the client. A cap can block outright or route
    the order to an approver — most clients want the second, because refusing a
    guest a coffee is worse than asking a manager."""
    _name = 'care.hosp.limit'
    _description = 'Hospitality Consumption Limit'
    _order = 'sequence, id'

    name = fields.Char(string='Policy', required=True, translate=True)
    sequence = fields.Integer(default=10)
    facility_id = fields.Many2one('care.cafm.facility', string='Facility',
                                  help='Leave it empty to apply it to all facilities.')
    scope = fields.Selection([
        ('user', 'Specific User'), ('department', 'Department'), ('all', 'Everyone'),
    ], string='Scope', default='all', required=True)
    user_ids = fields.Many2many('res.users', string='Users')
    department_ids = fields.Many2many('hr.department', string='Departments')
    category_id = fields.Many2one('care.hosp.category', string='Restricted to Category',
                                  help='Leave it empty to include all categories.')
    period = fields.Selection([('day', 'Daily'), ('week', 'Weekly'), ('month', 'Monthly')],
                              string='Period', default='day', required=True)
    max_items = fields.Integer(string='Max Number of Items', default=0,
                               help='Zero = no limit.')
    max_orders = fields.Integer(string='Max Number of Orders', default=0)
    max_cost = fields.Float(string='Max Cost', default=0.0)
    on_exceed = fields.Selection([
        ('approve', 'Needs Approval'), ('block', 'Block Order'), ('warn', 'Warn Only'),
    ], string='On Exceed', default='approve', required=True)
    approver_ids = fields.Many2many('res.users', 'hosp_limit_approver_rel', 'limit_id', 'user_id',
                                    string='Approvers')
    exempt_vip = fields.Boolean(string='Exempt VIP Hospitality and Meetings', default=True,
                                help='Meeting and visitor orders are not counted against the employee limit.')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    # ---- evaluation ----
    def _period_start(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        if self.period == 'day':
            start = today
        elif self.period == 'week':
            start = today - timedelta(days=today.weekday())
        else:
            start = today.replace(day=1)
        return fields.Datetime.to_datetime(start)

    @api.model
    def _matching(self, order):
        """Policies that apply to this order, most specific first."""
        dom = ['|', ('facility_id', '=', False), ('facility_id', '=', order.facility_id.id)]
        pols = self.sudo().search(dom)
        out = self.browse()
        for p in pols:
            if p.category_id and p.category_id not in order.line_ids.mapped('category_id'):
                continue
            if p.scope == 'user' and order.requester_id not in p.user_ids:
                continue
            if p.scope == 'department' and order.department_id not in p.department_ids:
                continue
            out |= p
        return out

    @api.model
    def check_order(self, order):
        """Returns {'blocked'|'needs_approval'|'ok', 'message'} for one order."""
        pols = self._matching(order)
        if not pols:
            return {'ok': True}
        Line = self.env['care.hosp.order.line'].sudo()
        worst = {'ok': True}
        for p in pols:
            if p.exempt_vip and (order.is_vip or order.order_type in ('meeting', 'guest')):
                continue
            start = p._period_start()
            dom = [('requester_id', '=', order.requester_id.id),
                   ('order_id.placed_at', '>=', start),
                   ('order_state', 'not in', ('cancelled', 'rejected', 'draft'))]
            if p.category_id:
                dom.append(('category_id', '=', p.category_id.id))
            if p.facility_id:
                dom.append(('facility_id', '=', p.facility_id.id))
            used = Line.search(dom)
            used_items = sum(used.mapped('quantity'))
            used_cost = sum(used.mapped('line_cost'))
            used_orders = len(set(used.mapped('order_id').ids))
            new_items = sum(order.line_ids.mapped('quantity'))
            new_cost = sum(order.line_ids.mapped('line_cost'))

            hit = None
            if p.max_items and used_items + new_items > p.max_items:
                hit = _('Item limit exceeded (%(m)s %(per)s) — consumed %(u)s.') % {
                    'm': p.max_items, 'per': dict(p._fields['period'].selection)[p.period],
                    'u': int(used_items)}
            elif p.max_orders and used_orders + 1 > p.max_orders:
                hit = _('Order limit exceeded (%(m)s %(per)s).') % {
                    'm': p.max_orders, 'per': dict(p._fields['period'].selection)[p.period]}
            elif p.max_cost and used_cost + new_cost > p.max_cost:
                hit = _('Cost limit exceeded (%(m)s).') % {'m': p.max_cost}
            if not hit:
                continue
            msg = '%s — %s' % (p.name, hit)
            if p.on_exceed == 'block':
                return {'blocked': True, 'message': msg}
            if p.on_exceed == 'approve':
                worst = {'needs_approval': True, 'message': msg}
            elif worst.get('ok'):
                worst = {'ok': True, 'warning': msg}
        return worst

    @api.model
    def approvers_for(self, order):
        users = self.env['res.users']
        for p in self._matching(order):
            users |= p.approver_ids
        if not users:
            users = self.env.ref('base.user_admin', raise_if_not_found=False) or users
        return users

    @api.model
    def usage_for(self, user, facility=None):
        """What this person has consumed against every policy that binds them —
        drives the "المتبقّي لك اليوم" line in the portal."""
        Line = self.env['care.hosp.order.line'].sudo()
        out = []
        for p in self.sudo().search([]):
            if p.scope == 'user' and user not in p.user_ids:
                continue
            if facility and p.facility_id and p.facility_id != facility:
                continue
            ldom = [('requester_id', '=', user.id),
                    ('order_id.placed_at', '>=', p._period_start()),
                    ('order_state', 'not in', ('cancelled', 'rejected', 'draft'))]
            if p.category_id:
                ldom.append(('category_id', '=', p.category_id.id))
            used = Line.search(ldom)
            out.append({
                'policy': p.name, 'period': p.period,
                'max_items': p.max_items, 'used_items': int(sum(used.mapped('quantity'))),
                'max_cost': p.max_cost, 'used_cost': sum(used.mapped('line_cost')),
                'on_exceed': p.on_exceed,
            })
        return out


class HospFavorite(models.Model):
    """"طلبي المعتاد" — the whole point of a hospitality app is that the third
    coffee of the week takes one tap, not six."""
    _name = 'care.hosp.favorite'
    _description = 'Favorites'
    _order = 'sequence, id'

    name = fields.Char(string='Name', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True,
                              default=lambda s: s.env.user, ondelete='cascade', index=True)
    item_id = fields.Many2one('care.hosp.item', string='Item', required=True)
    option_ids = fields.Many2many('care.hosp.option', string='Options')
    quantity = fields.Float(string='Quantity', default=1.0)
    note = fields.Char(string='Note')
    sequence = fields.Integer(default=10)
    times_used = fields.Integer(string='Times Used', default=0)


class HospStanding(models.Model):
    """A standing order — "قهوتي كل يوم عمل الساعة ٨". The cron places it, so
    the kitchen sees the morning rush before it walks in."""
    _name = 'care.hosp.standing'
    _description = 'Standing Order'
    _order = 'time_of_day'

    name = fields.Char(string='Name', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True,
                              default=lambda s: s.env.user, ondelete='cascade')
    facility_id = fields.Many2one('care.cafm.facility', string='Facility', required=True)
    location_id = fields.Many2one('care.cafm.location', string='Location')
    room_label = fields.Char(string='Office')
    item_id = fields.Many2one('care.hosp.item', string='Item', required=True)
    option_ids = fields.Many2many('care.hosp.option', string='Options')
    quantity = fields.Float(string='Quantity', default=1.0)
    time_of_day = fields.Float(string='Hour', default=8.0, required=True)
    weekdays_only = fields.Boolean(string='Working Days Only', default=True)
    last_run = fields.Date(string='Last Run', readonly=True)
    active = fields.Boolean(default=True)

    @api.model
    def _cron_place_standing(self):
        """Places any standing order whose time has come today. Runs often; the
        last_run date makes it idempotent so a re-run never double-orders."""
        now = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        today = now.date()
        h = now.hour + now.minute / 60.0
        for s in self.search([('last_run', '!=', today)]):
            if s.weekdays_only and today.weekday() in (4, 5):  # Fri/Sat weekend
                continue
            if h < s.time_of_day:
                continue
            order = self.env['care.hosp.order'].with_user(s.user_id).create({
                'requester_id': s.user_id.id, 'facility_id': s.facility_id.id,
                'location_id': s.location_id.id or False, 'room_label': s.room_label,
                'note': _('Standing order: %s') % s.name,
                'line_ids': [(0, 0, {'item_id': s.item_id.id, 'quantity': s.quantity,
                                     'option_ids': [(6, 0, s.option_ids.ids)]})],
            })
            try:
                order.action_place()
            except Exception:
                order.action_cancel()
            s.last_run = today
        return True


class ResUsersHospitality(models.Model):
    """Where this person is served.

    A guest typing their office number into every order is how orders arrive at
    the wrong desk. The place is a property of the person, set once — by the
    location's own QR code or by name — and changeable when they move desks or
    order for a meeting room instead.
    """
    _inherit = 'res.users'

    hosp_location_id = fields.Many2one(
        'care.cafm.location', string='Usual Serving Place',
        help='Filled in automatically on every hospitality order, and can be changed when ordering.')
    hosp_room_label = fields.Char(
        string='Office/Hall',
        help='Used when the place is not registered as a location in the system.')
    hosp_location_locked = fields.Boolean(
        string='Lock Place', default=False,
        help='When enabled the user cannot change the place while ordering — '
             'only the client administrator can set it.')

    def hosp_place(self):
        """(location, label) for this user, whatever was filled in."""
        self.ensure_one()
        return self.hosp_location_id, (
            self.hosp_room_label or self.hosp_location_id.name or '')

    def hosp_set_place(self, location_id=None, room_label=None, code=None):
        """Set the default place, resolving a scanned location code if given."""
        self.ensure_one()
        if self.hosp_location_locked and not self.env.user._is_admin():
            raise UserError(_('The serving place is locked — contact the account administrator to change it.'))
        if code:
            loc = self.env['care.cafm.location'].sudo().search(
                [('code', '=', code)], limit=1)
            if not loc:
                raise UserError(_('There is no location with this code: %s') % code)
            location_id = loc.id
        vals = {}
        if location_id is not None:
            vals['hosp_location_id'] = location_id or False
        if room_label is not None:
            vals['hosp_room_label'] = room_label or False
        if vals:
            self.sudo().write(vals)
        return True
