# -*- coding: utf-8 -*-
"""The vehicle behind the plate.

A valet ticket is a single visit. But the same cars come back — a consultant's
car every Tuesday, a supplier's van every morning — and re-typing the make,
colour and owner each time is both slow and how a car ends up logged twice
under two spellings.

So the plate is the identity. Scan or type it and, if it has been here before,
everything already known about it is filled in and its history is one tap
away. What the camera reads is normalised before matching: Arabic-Indic digits
become Latin, separators and spacing are dropped, so ١٢٣٤٥/ب and 12345 B are
the same car.
"""
import re
from datetime import timedelta

from odoo import api, fields, models, _

# ٠١٢٣٤٥٦٧٨٩ and ۰۱۲۳۴۵۶۷۸۹ both appear on Gulf plates and in OCR output.
_DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', '01234567890123456789')


def normalise_plate(raw):
    """A comparable key for a plate: Latin digits, no separators, upper case.

    Matching on the raw string fails on exactly the differences that do not
    matter — a slash, a space, or Arabic numerals from the camera.
    """
    if not raw:
        return ''
    s = str(raw).translate(_DIGITS).upper()
    return re.sub(r'[^0-9A-Zء-ي]', '', s)


class ValetVehicle(models.Model):
    _name = 'care.valet.vehicle'
    _description = 'Registered Vehicle'
    _inherit = ['mail.thread']
    _order = 'last_seen desc, id desc'
    _rec_name = 'plate'

    plate = fields.Char(string='Plate Number', required=True, tracking=True, index=True)
    plate_key = fields.Char(string='Match Key', compute='_compute_key', store=True,
                            index=True,
                            help='The normalised plate — used to match what the camera reads.')
    make = fields.Char(string='Make', tracking=True)
    model = fields.Char(string='Model', tracking=True)
    color = fields.Char(string='Color', tracking=True)
    owner_name = fields.Char(string='Owner Name', tracking=True)
    owner_phone = fields.Char(string='Owner Phone', tracking=True)
    owner_type = fields.Selection([
        ('guest', 'Visitor'), ('staff', 'Employee'), ('patient', 'Patient'),
        ('supplier', 'Supplier'), ('vip', 'VIP'),
    ], string='Category', default='guest', required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', tracking=True)
    facility_id = fields.Many2one('care.cafm.facility', string='Facility', index=True,
                                  tracking=True)

    # ---- standing instructions that should survive between visits ----------
    vip = fields.Boolean(string='VIP', tracking=True,
                         help='The team is alerted as soon as the vehicle checks in.')
    blocked = fields.Boolean(string='Blocked', tracking=True)
    block_reason = fields.Char(string='Block Reason', tracking=True)
    notes = fields.Text(string='Permanent Notes',
                        help='For example: left door handle already damaged, or manual transmission.')
    preferred_zone_id = fields.Many2one('care.valet.zone', string='Preferred Spot')

    ticket_ids = fields.One2many('care.valet.ticket', 'vehicle_id', string='Visits')
    visit_count = fields.Integer(string='Visit Count', compute='_compute_stats',
                                 store=True)
    last_seen = fields.Datetime(string='Last Visit', compute='_compute_stats', store=True)
    first_seen = fields.Datetime(string='First Visit', compute='_compute_stats', store=True)
    avg_stay_minutes = fields.Float(string='Average Stay (Minutes)',
                                    compute='_compute_stats', store=True)
    is_regular = fields.Boolean(string='Frequent Visitor', compute='_compute_stats', store=True,
                                help='Three or more visits in the last ninety days.')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [('plate_key_uniq', 'unique(plate_key, company_id)',
                         'This plate is already registered.')]

    @api.depends('plate')
    def _compute_key(self):
        for v in self:
            v.plate_key = normalise_plate(v.plate)

    @api.depends('ticket_ids.received_at', 'ticket_ids.state')
    def _compute_stats(self):
        cutoff = fields.Datetime.now() - timedelta(days=90)
        for v in self:
            visits = v.ticket_ids.sorted('received_at')
            v.visit_count = len(visits)
            v.first_seen = visits[:1].received_at if visits else False
            v.last_seen = visits[-1:].received_at if visits else False
            stays = [
                (t.delivered_at - t.received_at).total_seconds() / 60.0
                for t in visits if t.delivered_at and t.received_at]
            v.avg_stay_minutes = (sum(stays) / len(stays)) if stays else 0.0
            v.is_regular = len([t for t in visits
                                if t.received_at and t.received_at >= cutoff]) >= 3

    @api.model
    def find_by_plate(self, plate):
        """The lookup a camera scan performs. Returns an empty set, not None,
        so callers can treat 'unknown car' as an ordinary case."""
        key = normalise_plate(plate)
        return self.search([('plate_key', '=', key)], limit=1) if key else self.browse()

    @api.model
    def resolve(self, plate, vals=None):
        """Find this plate or register it, and keep what we learn.

        A visit often knows more than the record does — the guest gives a phone
        number, the crew notes the colour. Filling only the blanks means a
        later visit never overwrites something a person corrected by hand.
        """
        vehicle = self.find_by_plate(plate)
        vals = {k: v for k, v in (vals or {}).items() if v}
        if not vehicle:
            return self.create(dict(vals, plate=plate))
        fill = {k: v for k, v in vals.items()
                if k in self._fields and not vehicle[k]}
        if fill:
            vehicle.write(fill)
        return vehicle

    def action_tickets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Visits of %s') % self.plate,
            'res_model': 'care.valet.ticket', 'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id, 'default_plate': self.plate},
        }


class ValetTicketVehicle(models.Model):
    """Tie every ticket to its vehicle, so a plate accumulates a history."""
    _inherit = 'care.valet.ticket'

    vehicle_id = fields.Many2one('care.valet.vehicle', string='Vehicle', index=True,
                                 ondelete='set null', tracking=True)
    vehicle_known = fields.Boolean(string='Known Vehicle', compute='_compute_known',
                                   store=True)
    visit_number = fields.Integer(string='Visit Number', compute='_compute_known',
                                  store=True)

    @api.depends('vehicle_id', 'vehicle_id.visit_count')
    def _compute_known(self):
        for t in self:
            t.vehicle_known = bool(t.vehicle_id and t.vehicle_id.visit_count > 1)
            t.visit_number = t.vehicle_id.visit_count if t.vehicle_id else 0

    @api.model_create_multi
    def create(self, vals_list):
        tickets = super().create(vals_list)
        for t in tickets:
            if t.plate and not t.vehicle_id:
                t.vehicle_id = self.env['care.valet.vehicle'].sudo().resolve(
                    t.plate, {
                        'make': t.car_make, 'model': t.car_model, 'color': t.car_color,
                        'owner_name': t.guest_name, 'owner_phone': t.guest_phone,
                        'facility_id': t.facility_id.id,
                    }).id
            v = t.vehicle_id
            if v and v.blocked:
                t.message_post(body=_('⛔ Blocked vehicle: %s') % (v.block_reason or ''))
            elif v and v.vip:
                t.message_post(body=_('⭐ VIP vehicle — priority handover.'))
            elif v and v.notes:
                t.message_post(body=_('📌 Permanent notes on this vehicle: %s') % v.notes)
        return tickets


class ValetDriver(models.Model):
    """The crew who actually park the cars.

    A supervisor could see tickets but had no way to say who is on the floor
    and who takes the next car. Without that, "where is my car" has no owner
    and the parking spot is whatever the guest was told verbally.
    """
    _name = 'care.valet.driver'
    _description = 'Valet Driver'
    _inherit = ['mail.thread']
    _order = 'active desc, name'

    name = fields.Char(string='Name', required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', tracking=True)
    user_id = fields.Many2one('res.users', string='App user', tracking=True,
                              help='The account this driver signs in with.')
    phone = fields.Char(string='Phone', tracking=True)
    facility_id = fields.Many2one('care.cafm.facility', string='Facility',
                                  required=True, index=True, tracking=True)
    zone_ids = fields.Many2many('care.valet.zone', string='Zones covered')
    on_shift = fields.Boolean(string='On shift', default=False, tracking=True)
    shift_started = fields.Datetime(string='Shift started', readonly=True)

    ticket_ids = fields.One2many('care.valet.ticket', 'driver_id', string='Cars handled')
    open_count = fields.Integer(string='Cars in hand', compute='_compute_load')
    today_count = fields.Integer(string='Handled today', compute='_compute_load')
    avg_park_minutes = fields.Float(string='Average park time (minutes)',
                                    compute='_compute_load')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def _compute_load(self):
        today = fields.Date.context_today(self)
        for d in self:
            tickets = d.ticket_ids
            d.open_count = len(tickets.filtered(
                lambda t: t.state in ('received', 'parked', 'requested')))
            d.today_count = len(tickets.filtered(
                lambda t: t.received_at and str(t.received_at)[:10] == str(today)))
            spans = [(t.parked_at - t.received_at).total_seconds() / 60.0
                     for t in tickets
                     if getattr(t, 'parked_at', False) and t.received_at]
            d.avg_park_minutes = (sum(spans) / len(spans)) if spans else 0.0

    def action_toggle_shift(self):
        for d in self:
            d.write({'on_shift': not d.on_shift,
                     'shift_started': fields.Datetime.now() if not d.on_shift else False})
        return True

    @api.model
    def next_free(self, facility_id, zone_id=None):
        """Whoever is on shift with the fewest cars in hand.

        Round-robin by name would hand the tenth car to someone already
        holding four; load is the only fair basis.
        """
        dom = [('facility_id', '=', facility_id), ('on_shift', '=', True)]
        if zone_id:
            dom.append(('zone_ids', 'in', [zone_id]))
        drivers = self.search(dom)
        if not drivers:
            return self.browse()
        return min(drivers, key=lambda d: d.open_count)


class ValetTicketDriver(models.Model):
    """Who has the car, and exactly where they left it."""
    _inherit = 'care.valet.ticket'

    driver_id = fields.Many2one('care.valet.driver', string='Driver', index=True,
                                tracking=True)
    parked_at = fields.Datetime(string='Parked at', readonly=True, copy=False)
    park_row = fields.Char(string='Row / bay', tracking=True,
                           help='What the driver writes on the slip: B2-14, '
                                'basement row 3, and so on.')
    park_note = fields.Char(string='Parking note',
                            help='Anything that helps find it again — beside '
                                 'the pillar, second level, behind the van.')
    # The phone knows where it is; asking the driver to describe it is how a
    # car goes missing on a busy evening.
    park_lat = fields.Float(string='Latitude', digits=(10, 7), readonly=True)
    park_lng = fields.Float(string='Longitude', digits=(10, 7), readonly=True)
    park_located = fields.Boolean(string='Location captured',
                                  compute='_compute_located', store=True)
    park_map_url = fields.Char(string='Map link', compute='_compute_located')

    @api.depends('park_lat', 'park_lng')
    def _compute_located(self):
        for t in self:
            t.park_located = bool(t.park_lat and t.park_lng)
            t.park_map_url = ('https://maps.google.com/?q=%s,%s'
                              % (t.park_lat, t.park_lng)) if t.park_located else False

    def action_park(self, row=None, note=None, lat=None, lng=None, driver_id=None):
        """Record where the car actually is, at the moment it is left there."""
        for t in self:
            vals = {'state': 'parked', 'parked_at': fields.Datetime.now()}
            if row:
                vals['park_row'] = row
            if note:
                vals['park_note'] = note
            if lat and lng:
                vals['park_lat'] = float(lat)
                vals['park_lng'] = float(lng)
            if driver_id:
                vals['driver_id'] = int(driver_id)
            elif not t.driver_id:
                d = self.env['care.valet.driver'].sudo().next_free(
                    t.facility_id.id, t.zone_id.id or None)
                if d:
                    vals['driver_id'] = d.id
            t.write(vals)
            t.message_post(body=_('🅿️ Parked at %s%s') % (
                row or t.park_row or '—',
                _(' · location captured') if (lat and lng) else ''))
        return True
