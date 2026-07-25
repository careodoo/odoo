# -*- coding: utf-8 -*-
"""Waste Transfer & Treatment — a self-contained CAFM service.

A client requests a waste pickup from their premises; we dispatch a crew + truck
to collect it, then transport it for treatment and finally to the government
incinerator, giving the client full reports at every stage.

This is a ground-up, smarter re-architecture of the legacy ``service_order``
module, living **inside** the CAFM ecosystem on its own tables — but every
data-bearing field keeps the *same name* as in ``service_order`` so records can
be migrated across 1:1 later. The state machine is driven from the order itself
(the trip follows), roles + proof live on the order, and a single
``dashboard_stats`` feeds both the portal and the app.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError

STATES = [
    ('draft', 'Draft'),
    ('scheduled', 'Scheduled'),
    ('pickuped', 'Picked Up'),
    ('arrived', 'Arrived at Treatment'),
    ('processing', 'Under Treatment'),
    ('delivered', 'Delivered to Incinerator'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
]
OPEN_STATES = ('draft', 'scheduled', 'pickuped', 'arrived', 'processing')
FLOW = ['draft', 'scheduled', 'pickuped', 'arrived', 'processing', 'delivered', 'completed']


class WasteType(models.Model):
    _name = 'cafm.waste.type'
    _description = 'Waste Order Type'
    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)


class WasteCenter(models.Model):
    _name = 'cafm.waste.center'
    _description = 'Treatment Centre / Incinerator'
    name = fields.Char(required=True, translate=True)
    is_incinerator = fields.Boolean(string='Government Incinerator')
    address = fields.Char()
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)


class WasteItem(models.Model):
    _name = 'cafm.waste.item'
    _description = 'Waste Item'
    _inherit = ['mail.thread']
    name = fields.Char(required=True, translate=True)
    image = fields.Binary(string='Image')
    type_id = fields.Many2one('cafm.waste.type', string='Type', tracking=True)
    notes = fields.Html()
    width = fields.Float(string='Width', tracking=True)
    height = fields.Float(string='Height', tracking=True)
    weight = fields.Float(string='Weight (kg)', tracking=True)
    active = fields.Boolean(default=True)


class WastePickupLocation(models.Model):
    _name = 'cafm.waste.pickup.location'
    _description = 'Pickup Location'
    name = fields.Char(required=True)
    address = fields.Char(string='Address')
    project_id = fields.Many2one('cafm.waste.project', string='Project')
    active = fields.Boolean(default=True)


class WasteTeam(models.Model):
    _name = 'cafm.waste.team'
    _description = 'Waste Collection Team'
    name = fields.Char(required=True)
    project_id = fields.Many2one('cafm.waste.project', string='Project')
    employee_ids = fields.Many2many('hr.employee', string='Members')
    member_count = fields.Integer(compute='_compute_member_count')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    def _compute_member_count(self):
        for t in self:
            t.member_count = len(t.employee_ids)


class WasteProject(models.Model):
    _name = 'cafm.waste.project'
    _description = 'Waste Project (Client Contract)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(required=True, tracking=True)
    sequence = fields.Char(string='Sequence Number', readonly=True, copy=False)
    active = fields.Boolean(default=True)
    contact_id = fields.Many2one('res.partner', string='Client Entity', tracking=True)
    cafm_client_id = fields.Many2one('care.cafm.client', string='Facility Client', tracking=True)
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    image = fields.Binary()
    notes = fields.Html()
    pickup_location_ids = fields.One2many('cafm.waste.pickup.location', 'project_id', string='Pickup Locations')
    team_ids = fields.One2many('cafm.waste.team', 'project_id', string='Teams')
    # ---- default operation team (new orders inherit these; still editable) ----
    default_ops_manager_id = fields.Many2one(
        'res.users', string='Default Operations Officer', tracking=True,
        help='Notified as soon as any new transfer order arrives in this project, and assigns the driver.')
    driver_user_ids = fields.Many2many(
        'res.users', 'cafm_waste_project_driver_rel', 'project_id', 'user_id',
        string='Drivers Registered in the Service', tracking=True,
        help='The pool of drivers the operations officer selects from when assigning the order.')
    default_driver_id = fields.Many2one(
        'res.users', string='Default Driver', tracking=True,
        domain="[('id','in',driver_user_ids)]",
        help='Optional — assigned automatically to new orders. Leave empty so the operations officer assigns manually.')
    default_receiver_id = fields.Many2one(
        'res.users', string='Default Quantity Receiver', tracking=True,
        help='The treatment centre receiver who records the received quantities.')
    order_ids = fields.One2many('cafm.waste.order', 'project_id', string='Orders')
    trip_ids = fields.One2many('cafm.waste.trip', 'project_id', string='Trips')
    order_count = fields.Integer(compute='_compute_counts')
    trip_count = fields.Integer(compute='_compute_counts')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def _compute_counts(self):
        for p in self:
            p.order_count = len(p.order_ids)
            p.trip_count = len(p.trip_ids)

    @api.onchange('cafm_client_id')
    def _onchange_client(self):
        if self.cafm_client_id and self.cafm_client_id.partner_id:
            self.contact_id = self.cafm_client_id.partner_id

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if not v.get('sequence'):
                v['sequence'] = self.env['ir.sequence'].next_by_code('cafm.waste.project') or '/'
        return super().create(vals_list)


class WasteOrderLine(models.Model):
    _name = 'cafm.waste.order.line'
    _description = 'Waste Order Line'
    order_id = fields.Many2one('cafm.waste.order', string='Order', ondelete='cascade')
    item_id = fields.Many2one('cafm.waste.item', string='Item', required=True)
    width = fields.Float(related='item_id.width', string='Width')
    height = fields.Float(related='item_id.height', string='Height')
    weight = fields.Float(related='item_id.weight', string='Weight')
    quantity = fields.Float(string='Quantity', default=1.0)
    active = fields.Boolean(default=True)


class WasteTripLine(models.Model):
    _name = 'cafm.waste.trip.line'
    _description = 'Waste Trip Line'
    trip_id = fields.Many2one('cafm.waste.trip', string='Trip', ondelete='cascade')
    order_id = fields.Many2one('cafm.waste.order', string='Order')
    item_id = fields.Many2one('cafm.waste.item', string='Item', required=True)
    width = fields.Float(related='item_id.width', string='Width')
    height = fields.Float(related='item_id.height', string='Height')
    weight = fields.Float(related='item_id.weight', string='Weight')
    quantity = fields.Float(string='Quantity', default=1.0)
    active = fields.Boolean(default=True)


class WasteTrip(models.Model):
    _name = 'cafm.waste.trip'
    _description = 'Waste Transfer Trip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence desc, id desc'
    _rec_name = 'sequence'

    sequence = fields.Char(string='Sequence Number', readonly=True, copy=False)
    reference = fields.Char(string='Reference', compute='_compute_reference', store=True)
    pickup_location_id = fields.Many2one('cafm.waste.pickup.location', string='Pickup Location', tracking=True)
    center_id = fields.Many2one('cafm.waste.center', string='Treatment Centre', tracking=True)
    type_id = fields.Many2one('cafm.waste.type', string='Type', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda s: s.env.company)
    project_id = fields.Many2one('cafm.waste.project', string='Project', tracking=True)
    pickuped_datetime = fields.Datetime(string='Pickup Time', tracking=True)
    contact_id = fields.Many2one('res.partner', string='Client Entity', tracking=True)
    trip_date = fields.Date(string='Trip Date', tracking=True)
    trip_line_ids = fields.One2many('cafm.waste.trip.line', 'trip_id', string='Items')
    states = fields.Selection(STATES, string='Status', default='draft', tracking=True)
    team_id = fields.Many2one('cafm.waste.team', string='Team', tracking=True)
    order_id = fields.Many2one('cafm.waste.order', string='Order')
    media_ids = fields.Many2many('ir.attachment', 'cafm_waste_trip_media_rel', 'trip_id', 'attachment_id',
                                 string='Trip Photos and Videos')
    # live driver GPS tracking
    driver_id = fields.Many2one('res.users', string='Driver', tracking=True)
    # driver acknowledgement — the crew accepts the job before moving
    driver_accepted = fields.Boolean(string='Driver Accepted', copy=False, tracking=True)
    driver_accepted_at = fields.Datetime(string='Acceptance Time', copy=False)
    driver_lat = fields.Float(string='Latitude', digits=(10, 7))
    driver_lng = fields.Float(string='Longitude', digits=(10, 7))
    driver_loc_time = fields.Datetime(string='Last Location Update')
    # stored so they can be grouped/sorted/aggregated (same reason as the order)
    total_weight = fields.Float(compute='_compute_totals', store=True, string='Total Item Weights')
    total_quantity = fields.Float(compute='_compute_totals', store=True, string='Total Quantity')
    total_qty_weight = fields.Float(compute='_compute_totals', store=True, string='Total Weight')
    active = fields.Boolean(default=True)

    @api.depends('trip_line_ids.quantity', 'trip_line_ids.weight', 'trip_line_ids.item_id.weight')
    def _compute_totals(self):
        for t in self:
            t.total_weight = round(sum(t.trip_line_ids.mapped('weight')), 1)
            t.total_quantity = round(sum((l.quantity or 0) for l in t.trip_line_ids), 1)
            t.total_qty_weight = round(sum((l.quantity or 0) * (l.weight or 0) for l in t.trip_line_ids), 1)

    @api.depends('sequence', 'project_id.sequence')
    def _compute_reference(self):
        for t in self:
            t.reference = '%s - %s' % (t.sequence or '', t.project_id.sequence or '')

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if not v.get('sequence'):
                v['sequence'] = self.env['ir.sequence'].next_by_code('cafm.waste.trip') or '/'
        trips = super().create(vals_list)
        for t in trips:
            t._notify_driver()
        return trips

    def write(self, vals):
        res = super().write(vals)
        if vals.get('driver_id'):
            for t in self:
                t._notify_driver()
        return res

    def _notify_driver(self):
        self.ensure_one()
        if not self.driver_id or 'care.cafm.notification' not in self.env:
            return
        try:
            self.env['care.cafm.notification'].sudo().push(
                self.driver_id, _('🚛 New Waste Trip %s') % (self.sequence or ''),
                _('Trip %s has been assigned to you — pickup from %s. Open Waste Trips to share your location.')
                % (self.sequence or '', self.pickup_location_id.name or '—'),
                ntype='task', record=self)
        except Exception:
            pass

    def _get_report_base_filename(self):
        self.ensure_one()
        return '%s' % (self.reference or self.sequence)


class WasteOrder(models.Model):
    _name = 'cafm.waste.order'
    _description = 'Waste Transfer and Treatment Order'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'serial desc, id desc'
    _rec_name = 'serial'

    serial = fields.Char(string='Sequence Number', readonly=True, copy=False)
    active = fields.Boolean(default=True)
    project_id = fields.Many2one('cafm.waste.project', string='Project', tracking=True)
    contact_id = fields.Many2one(related='project_id.contact_id', store=True, string='Client Entity')
    type_id = fields.Many2one('cafm.waste.type', string='Type', tracking=True)
    pickup_location_id = fields.Many2one('cafm.waste.pickup.location', string='Pickup Location', tracking=True)
    order_datetime = fields.Datetime(string='Pickup Time', tracking=True)
    request_datetime = fields.Datetime(string='Order Time', default=fields.Datetime.now)
    notes = fields.Html(string='Notes')
    states = fields.Selection(STATES, string='Status', default='draft', copy=False, tracking=True)
    order_line_ids = fields.One2many('cafm.waste.order.line', 'order_id', string='Items')
    trip_id = fields.Many2one('cafm.waste.trip', string='Trip', tracking=True)
    trip_line_ids = fields.One2many(related='trip_id.trip_line_ids', string='Trip Items')

    # operation roles + proof (live on the order — smarter than the legacy split)
    # defaulted from the project's team on create, but always editable afterwards.
    ops_manager_id = fields.Many2one('res.users', string='Operations Officer', tracking=True)
    driver_id = fields.Many2one('res.users', string='Driver', tracking=True,
                                domain="[('id','in',available_driver_ids)]")
    receiver_id = fields.Many2one('res.users', string='Quantity Receiver', tracking=True)
    # the project's driver pool — drives the driver_id domain in the form
    available_driver_ids = fields.Many2many(
        'res.users', string='Available Drivers',
        compute='_compute_available_drivers', help='The drivers registered in the project of this order.')
    proof_image = fields.Image(string='Proof Photo', max_width=1920, max_height=1920)
    media_ids = fields.Many2many('ir.attachment', 'cafm_waste_order_media_rel', 'order_id', 'attachment_id',
                                 string='Proof Photos and Videos',
                                 help='Additional photos and videos evidencing the collection and treatment work.')
    final_weight = fields.Float(string='Final Received Weight')
    final_note = fields.Char(string='Receipt Note')

    # stored: the graph/pivot dashboards aggregate these as measures, which is a
    # read_group → they must exist as real columns or Odoo raises
    # "Cannot convert field ... to SQL".
    total_quantity = fields.Float(compute='_compute_totals', store=True, string='Total Quantity')
    total_weight = fields.Float(compute='_compute_totals', store=True, string='Total Weight')
    qr_url = fields.Char(compute='_compute_qr_url', string='QR')

    def effective_lines(self):
        """Items to display for the order: its own lines, or the trip's lines
        (legacy data kept the items on the trip, not the order)."""
        self.ensure_one()
        return self.order_line_ids or (self.trip_id.trip_line_ids if self.trip_id else self.order_line_ids)

    # depend on item_id.weight too: line.weight is a *related non-stored* field,
    # so the stored total must follow the underlying source to stay correct.
    @api.depends('order_line_ids.quantity', 'order_line_ids.weight', 'order_line_ids.item_id.weight',
                 'trip_id', 'trip_id.trip_line_ids.quantity', 'trip_id.trip_line_ids.weight',
                 'trip_id.trip_line_ids.item_id.weight')
    def _compute_totals(self):
        for o in self:
            lines = o.effective_lines()
            o.total_quantity = round(sum(lines.mapped('quantity')), 1)
            o.total_weight = round(sum((l.quantity or 0) * (l.weight or 0) for l in lines), 1)

    @api.depends('project_id', 'project_id.driver_user_ids')
    def _compute_available_drivers(self):
        for o in self:
            o.available_driver_ids = o.project_id.driver_user_ids

    @api.onchange('project_id')
    def _onchange_project_team(self):
        """Pull the project's default team in as soon as the project is picked."""
        for o in self:
            p = o.project_id
            if not p:
                continue
            o.ops_manager_id = o.ops_manager_id or p.default_ops_manager_id
            o.receiver_id = o.receiver_id or p.default_receiver_id
            o.driver_id = o.driver_id or p.default_driver_id

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if not v.get('serial'):
                v['serial'] = self.env['ir.sequence'].next_by_code('cafm.waste.order') or '/'
            # inherit the project's default team (app/portal orders never pass these)
            if v.get('project_id'):
                p = self.env['cafm.waste.project'].browse(v['project_id'])
                v.setdefault('ops_manager_id', p.default_ops_manager_id.id or False)
                v.setdefault('receiver_id', p.default_receiver_id.id or False)
                if p.default_driver_id:
                    v.setdefault('driver_id', p.default_driver_id.id)
        orders = super().create(vals_list)
        for o in orders:
            o._notify_roles()
            o._notify_new_order()
        return orders

    def _notify_new_order(self):
        """Tell the ops manager a request landed so they can assign a driver."""
        self.ensure_one()
        mgr = self.ops_manager_id or self.project_id.default_ops_manager_id
        if not mgr:
            return
        if mgr.partner_id:
            self.message_subscribe(partner_ids=mgr.partner_id.ids)
        body = _('New Transfer Order %s — %s%s') % (
            self.serial or '', self.project_id.name or '',
            _(' · Awaiting driver assignment') if not self.driver_id else '')
        self.message_post(body=body, partner_ids=mgr.partner_id.ids if mgr.partner_id else None)
        if 'care.cafm.notification' in self.env:
            try:
                self.env['care.cafm.notification'].sudo().push(
                    mgr, _('🗑️ New Waste Transfer Order'), body, ntype='task',
                    action_url='/waste/order/%s' % self.id, record=self)
            except Exception:
                pass
        # no driver yet → raise a real To-Do so the assignment can't be missed
        if not self.driver_id:
            try:
                self.activity_schedule('mail.mail_activity_data_todo', user_id=mgr.id,
                                       summary=_('Assign a driver to order %s') % (self.serial or ''),
                                       note=body)
            except Exception:
                pass

    def action_assign_driver(self):
        """Open the assign-driver wizard (ops manager picks from the pool)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Assign Driver'),
            'res_model': 'cafm.waste.assign.driver',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id, 'default_driver_id': self.driver_id.id or False},
        }

    def assign_driver(self, driver):
        """Assign the driver and start the operation (order → scheduled)."""
        self.ensure_one()
        self.driver_id = driver.id
        # assignment is where the operation actually begins
        if self.states == 'draft':
            self.action_to_schedule()
        if self.trip_id:
            self.trip_id.driver_id = driver.id
        self.message_post(body=_('🚛 The order has been assigned to driver %s') % driver.name)
        # close the "assign a driver" to-do
        try:
            self.activity_ids.filtered(
                lambda a: a.user_id == self.ops_manager_id).action_feedback(
                    feedback=_('Driver %s has been assigned.') % driver.name)
        except Exception:
            pass
        return True

    def write(self, vals):
        res = super().write(vals)
        if {'ops_manager_id', 'driver_id', 'receiver_id'} & set(vals):
            for o in self:
                o._notify_roles()
        # keep the trip's driver in step with the order's. They are separate
        # fields, so editing one in the back-office silently drifted them apart —
        # and the driver's workspace filters trips by trip.driver_id, so the
        # assigned driver would stop seeing his own trip.
        if vals.get('driver_id'):
            for o in self:
                if o.trip_id and o.trip_id.driver_id.id != vals['driver_id']:
                    o.trip_id.driver_id = vals['driver_id']
        return res

    # ---- state machine (order drives; trip follows) ----------------------
    def _sync_trip(self, state):
        for o in self:
            if o.trip_id:
                o.trip_id.states = state

    def _ensure_trip(self):
        self.ensure_one()
        if self.trip_id:
            return self.trip_id
        trip = self.env['cafm.waste.trip'].create({
            'project_id': self.project_id.id,
            'type_id': self.type_id.id,
            'pickup_location_id': self.pickup_location_id.id,
            'contact_id': self.contact_id.id,
            'pickuped_datetime': self.order_datetime,
            'trip_date': fields.Date.context_today(self),
            'states': 'scheduled',
            'order_id': self.id,
            'trip_line_ids': [(0, 0, {'item_id': l.item_id.id, 'quantity': l.quantity,
                                      'order_id': self.id}) for l in self.order_line_ids],
        })
        self.trip_id = trip.id
        return trip

    def _advance(self, state, client_msg=True):
        for o in self:
            o.states = state
            o._sync_trip(state)
            if client_msg:
                o._notify_client(state)

    def action_to_schedule(self):
        for o in self:
            o._ensure_trip()
            o._advance('scheduled')

    def action_to_pickuped(self):
        self._advance('pickuped')

    def action_to_arrived(self):
        self._advance('arrived')

    def action_to_processing(self):
        self._advance('processing')

    def action_to_delivered(self):
        self._advance('delivered')

    def action_to_completed(self):
        self._advance('completed')

    def action_to_cancelled(self):
        self._advance('cancelled')

    def action_to_draft(self):
        self._advance('draft', client_msg=False)

    def _compute_access_url(self):
        super()._compute_access_url()
        for o in self:
            o.access_url = '/waste/order/%s' % o.id

    def _compute_qr_url(self):
        for o in self:
            o.qr_url = o.get_base_url() + (o.access_url or '')

    def _get_report_base_filename(self):
        self.ensure_one()
        return self.serial or 'waste-order'

    # ---- notifications ---------------------------------------------------
    _CLIENT_MSG = {
        'scheduled': ('📅 Your Order Has Been Scheduled', 'Waste collection order %s has been scheduled and the team will arrive shortly.'),
        'pickuped': ('🚛 Picked Up', 'The waste has been collected from your location for order %s.'),
        'arrived': ('🏭 Arrived at Treatment', 'The shipment for order %s has arrived at the treatment centre.'),
        'processing': ('♻️ Treatment in Progress', 'The waste for order %s is currently being treated.'),
        'delivered': ('🔥 Delivered to Incinerator', 'The waste for order %s has been delivered to the government incinerator.'),
        'completed': ('✅ Order Completed', 'Waste collection and treatment order %s has been completed. Thank you.'),
        'cancelled': ('✖ Order Cancelled', 'Waste order %s has been cancelled.'),
    }

    def _client_users(self):
        self.ensure_one()
        users = self.env['res.users'].sudo()
        p = self.contact_id
        if p:
            users |= self.env['res.users'].sudo().search([('partner_id', '=', p.id)])
            if 'care.cafm.client' in self.env:
                users |= self.env['care.cafm.client'].sudo().search(
                    [('partner_id', '=', p.id)]).mapped('user_ids')
        return users

    def _notify_client(self, state):
        self.ensure_one()
        msg = self._CLIENT_MSG.get(state)
        if not msg or 'care.cafm.notification' not in self.env:
            return
        users = self._client_users()
        if users:
            title, tpl = msg
            try:
                self.env['care.cafm.notification'].sudo().push(
                    users, title, tpl % (self.serial or ''), ntype='info',
                    action_url='/waste/order/%s' % self.id, record=self)
            except Exception:
                pass

    def _notify_roles(self):
        self.ensure_one()
        if 'care.cafm.notification' not in self.env:
            return
        for user, label in [(self.ops_manager_id, 'Operations Officer'),
                            (self.driver_id, 'Driver'), (self.receiver_id, 'Quantity Receiver')]:
            if user:
                try:
                    self.env['care.cafm.notification'].sudo().push(
                        user, _('Waste Order %s') % (self.serial or ''),
                        _('You have been assigned the role %s on order %s') % (label, self.serial or ''),
                        ntype='task', action_url='/waste/order/%s' % self.id, record=self)
                except Exception:
                    pass

    # ---- dashboard stats (feeds portal + app) ----------------------------
    @api.model
    def dashboard_stats(self, domain=None, date_from=None, date_to=None):
        dom = list(domain or [])
        if date_from:
            dom.append(('request_datetime', '>=', '%s 00:00:00' % date_from))
        if date_to:
            dom.append(('request_datetime', '<=', '%s 23:59:59' % date_to))
        recs = self.sudo().search(dom)
        by_state, by_item, by_month = {}, {}, {}
        tw = tq = completed = 0.0
        for o in recs:
            by_state[o.states] = by_state.get(o.states, 0) + 1
            if o.states in ('completed', 'delivered'):
                completed += 1
            dt = o.request_datetime or o.order_datetime
            mk = dt.strftime('%Y-%m') if dt else '—'
            m = by_month.setdefault(mk, {'orders': 0, 'weight': 0.0, 'qty': 0.0})
            m['orders'] += 1
            for l in o.effective_lines():
                q = l.quantity or 0
                w = q * (l.weight or 0)  # quantity × unit weight
                tq += q
                tw += w
                m['qty'] += q
                m['weight'] += w
                it = by_item.setdefault(l.item_id.name or '—',
                                        {'qty': 0.0, 'orders': 0, 'item_id': l.item_id.id})
                it['qty'] += q
                it['orders'] += 1
        months = sorted(by_month.items())
        maxm = max([v['orders'] for _, v in months], default=1) or 1
        top = sorted(by_item.items(), key=lambda x: -x[1]['qty'])[:8]
        return {
            'total_orders': len(recs),
            'open': sum(v for k, v in by_state.items() if k in OPEN_STATES),
            'completed': int(completed),
            'cancelled': by_state.get('cancelled', 0),
            'total_weight': round(tw, 1),
            'total_quantity': round(tq, 1),
            'by_month': [{'month': k, 'orders': v['orders'], 'weight': round(v['weight'], 1),
                          'qty': round(v['qty'], 1), 'pct': max(3, int(v['orders'] * 100 / maxm))}
                         for k, v in months],
            'by_item': [{'name': k, 'qty': v['qty'], 'orders': v['orders'], 'item_id': v['item_id']}
                        for k, v in top],
        }


class WasteAssignDriver(models.TransientModel):
    """Ops-manager wizard: pick a driver from the project's registered pool."""
    _name = 'cafm.waste.assign.driver'
    _description = 'Assign Driver to a Transfer Order'

    order_id = fields.Many2one('cafm.waste.order', string='Order', required=True, ondelete='cascade')
    project_id = fields.Many2one(related='order_id.project_id', string='Project')
    available_driver_ids = fields.Many2many(
        'res.users', string='Available Drivers',
        compute='_compute_available', help='The drivers registered in the project of this order.')
    driver_id = fields.Many2one('res.users', string='Driver', required=True,
                                domain="[('id','in',available_driver_ids)]")

    @api.depends('order_id')
    def _compute_available(self):
        for w in self:
            w.available_driver_ids = w.order_id.project_id.driver_user_ids

    def action_confirm(self):
        self.ensure_one()
        self.order_id.assign_driver(self.driver_id)
        return {'type': 'ir.actions.act_window_close'}


class WastePeriodReport(models.AbstractModel):
    """Data for the period SUMMARY report (totals + breakdowns), as opposed to
    the per-order report — printing one page per order for a whole month is a
    200-page document with no totals."""
    _name = 'report.care_cafm_waste.report_waste_period_doc'
    _description = 'Overall Waste Report for the Period'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        orders = self.env['cafm.waste.order'].browse(docids or []).exists()
        by_state, by_item, by_project = {}, {}, {}
        tq = tw = 0.0
        states = dict(STATES)
        for o in orders:
            lines = o.effective_lines()
            q = sum(l.quantity or 0 for l in lines)
            w = sum((l.quantity or 0) * (l.weight or 0) for l in lines)
            tq += q
            tw += w
            s = by_state.setdefault(o.states, {'label': states.get(o.states, o.states), 'orders': 0, 'qty': 0.0, 'weight': 0.0})
            s['orders'] += 1
            s['qty'] += q
            s['weight'] += w
            p = by_project.setdefault(o.project_id.id or 0, {'label': o.project_id.name or '—', 'orders': 0, 'qty': 0.0, 'weight': 0.0})
            p['orders'] += 1
            p['qty'] += q
            p['weight'] += w
            for l in lines:
                if not l.item_id:
                    continue
                it = by_item.setdefault(l.item_id.id, {'label': l.item_id.name, 'qty': 0.0, 'weight': 0.0})
                it['qty'] += l.quantity or 0
                it['weight'] += (l.quantity or 0) * (l.weight or 0)

        def rnd(rows, key='weight'):
            for r in rows:
                r['qty'] = round(r['qty'], 1)
                r['weight'] = round(r['weight'], 1)
            return sorted(rows, key=lambda r: -r[key])

        return {
            'doc_ids': orders.ids,
            'doc_model': 'cafm.waste.order',
            'docs': orders,
            'date_from': data.get('date_from'),
            'date_to': data.get('date_to'),
            'company': self.env.company,
            'totals': {'orders': len(orders), 'qty': round(tq, 1), 'weight': round(tw, 1)},
            'by_state': rnd(list(by_state.values()), 'orders'),
            'by_item': rnd(list(by_item.values())),
            'by_project': rnd(list(by_project.values()), 'orders'),
            'states': states,
        }
