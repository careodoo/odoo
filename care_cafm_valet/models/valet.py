# -*- coding: utf-8 -*-
"""Valet parking for CARE CAFM.

The full kerb-to-kerb cycle: a guest hands over a car, the attendant issues a
numbered ticket, parks it in a numbered bay, and later retrieves it on request —
with timing, charges, damage notes and shift takings all recorded."""
from datetime import timedelta
import secrets

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ValetZone(models.Model):
    """A parking area the service covers — a garage, a basement, a forecourt."""
    _name = 'care.valet.zone'
    _description = 'Valet Parking Zone'
    _order = 'facility_id, name'

    name = fields.Char(string='Zone', required=True, translate=True)
    code = fields.Char(string='Code')
    facility_id = fields.Many2one('care.cafm.facility', string='Facility', required=True)
    capacity = fields.Integer(string='Capacity (Spots)', default=50)
    spot_ids = fields.One2many('care.valet.spot', 'zone_id', string='Spots')
    occupied = fields.Integer(compute='_compute_stats', string='Occupied')
    free = fields.Integer(compute='_compute_stats', string='Available')
    occupancy = fields.Float(compute='_compute_stats', string='Occupancy %')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('spot_ids.state', 'capacity')
    def _compute_stats(self):
        for z in self:
            busy = len(z.spot_ids.filtered(lambda s: s.state == 'occupied'))
            total = len(z.spot_ids) or z.capacity or 0
            z.occupied = busy
            z.free = max(0, total - busy)
            z.occupancy = round(100.0 * busy / total, 1) if total else 0.0


class ValetSpot(models.Model):
    """One numbered bay."""
    _name = 'care.valet.spot'
    _description = 'Spot'
    _order = 'zone_id, name'

    name = fields.Char(string='Spot Number', required=True)
    zone_id = fields.Many2one('care.valet.zone', string='Zone', required=True, ondelete='cascade')
    facility_id = fields.Many2one(related='zone_id.facility_id', store=True, string='Facility')
    state = fields.Selection([
        ('free', 'Available'), ('occupied', 'Occupied'), ('blocked', 'Out of Service'),
    ], string='Status', default='free', required=True, index=True)
    ticket_id = fields.Many2one('care.valet.ticket', string='Current Ticket', readonly=True)
    note = fields.Char(string='Note')
    active = fields.Boolean(default=True)


class ValetTicket(models.Model):
    """A guest's car, from hand-over to hand-back."""
    _name = 'care.valet.ticket'
    _description = 'Valet Ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'received_at desc, id desc'

    name = fields.Char(string='Ticket Number', default='/', copy=False, readonly=True, index=True)
    facility_id = fields.Many2one('care.cafm.facility', string='Facility', required=True, tracking=True)
    zone_id = fields.Many2one('care.valet.zone', string='Zone', tracking=True,
                              domain="[('facility_id','=',facility_id)]")
    spot_id = fields.Many2one('care.valet.spot', string='Spot', tracking=True,
                              domain="[('zone_id','=',zone_id)]")
    # the car
    plate = fields.Char(string='Plate Number', required=True, tracking=True, index=True)
    car_make = fields.Char(string='Make')
    car_model = fields.Char(string='Model')
    car_color = fields.Char(string='Color')
    # the guest
    guest_name = fields.Char(string='Guest Name')
    guest_phone = fields.Char(string='Guest Phone', index=True)
    # the crew
    received_by = fields.Many2one('hr.employee', string='Checked In By', tracking=True)
    parked_by = fields.Many2one('hr.employee', string='Parked By')
    delivered_by = fields.Many2one('hr.employee', string='Handed Over By', tracking=True)
    shift_id = fields.Many2one('care.valet.shift', string='Shift', index=True)
    # timing
    received_at = fields.Datetime(string='Check-In Time', default=fields.Datetime.now, required=True, tracking=True)
    parked_at = fields.Datetime(string='Parking Time', readonly=True)
    requested_at = fields.Datetime(string='Request Time', readonly=True, tracking=True)
    delivered_at = fields.Datetime(string='Handover Time', readonly=True, tracking=True)
    park_minutes = fields.Float(string='Parking Duration (Minutes)', compute='_compute_times', store=True)
    retrieval_minutes = fields.Float(string='Retrieval Time (Minutes)', compute='_compute_times', store=True)
    sla_minutes = fields.Integer(string='Retrieval Target (Minutes)', default=7)
    is_late = fields.Boolean(string='Retrieval Delayed', compute='_compute_times', store=True)
    # money
    fee = fields.Float(string='Fees', tracking=True)
    tip = fields.Float(string='Tip')
    payment_method = fields.Selection([
        ('cash', 'Cash'), ('knet', 'KNET'), ('card', 'Card'), ('free', 'Complimentary/Guest'),
    ], string='Payment Method', default='cash', tracking=True)
    paid = fields.Boolean(string='Paid', tracking=True)
    # condition
    damage_note = fields.Text(string='Vehicle Condition Notes')
    has_damage = fields.Boolean(string='Has Damage Notes', tracking=True)
    key_tag = fields.Char(string='Key Tag Number')
    # A guest holds a printed ticket, not an account. The token on that ticket
    # is what lets them ask for the car back without logging in — so it must be
    # unguessable and belong to exactly one ticket.
    qr_token = fields.Char(string='Ticket Code', copy=False, index=True, readonly=True)
    requested_by_guest = fields.Boolean(string='Requested by Guest', readonly=True)
    state = fields.Selection([
        ('received', 'Checked In'), ('parked', 'Parked'), ('requested', 'Requested'),
        ('delivered', 'Delivered'), ('cancelled', 'Cancelled'),
    ], string='Status', default='received', required=True, tracking=True, index=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [('valet_name_uniq', 'unique(name)', 'The ticket number must be unique.')]

    @api.depends('received_at', 'delivered_at', 'requested_at', 'sla_minutes')
    def _compute_times(self):
        for t in self:
            t.park_minutes = ((t.delivered_at - t.received_at).total_seconds() / 60.0
                              if t.received_at and t.delivered_at else 0.0)
            t.retrieval_minutes = ((t.delivered_at - t.requested_at).total_seconds() / 60.0
                                   if t.requested_at and t.delivered_at else 0.0)
            t.is_late = bool(t.retrieval_minutes and t.sla_minutes
                             and t.retrieval_minutes > t.sla_minutes)

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', '/') == '/':
                v['name'] = self.env['ir.sequence'].next_by_code('care.valet.ticket') or '/'
            if v.get('damage_note'):
                v['has_damage'] = True
        return super().create(vals_list)

    # ---- the cycle -------------------------------------------------------
    def action_park(self, spot=None):
        """Attendant parked the car in a bay."""
        for t in self:
            if spot:
                t.spot_id = spot
            if not t.spot_id:
                raise UserError(_('Please select a parking spot first.'))
            if t.spot_id.state == 'occupied' and t.spot_id.ticket_id != t:
                raise UserError(_('Spot %s is already occupied.') % t.spot_id.name)
            t.write({'state': 'parked', 'parked_at': fields.Datetime.now(),
                     'parked_by': t.parked_by.id or t.received_by.id})
            t.spot_id.write({'state': 'occupied', 'ticket_id': t.id})
            t.message_post(body=_('🅿️ Parked in spot %s.') % t.spot_id.name)

    def action_request(self, by_guest=False):
        """Guest asked for the car back — starts the retrieval clock."""
        for t in self:
            t.write({'state': 'requested', 'requested_at': fields.Datetime.now(),
                     'requested_by_guest': by_guest})
            t.message_post(body=_('🔔 The guest requested vehicle retrieval%s.')
                           % (_(' (by scanning the ticket code)') if by_guest else ''))
            t._notify_crew()

    def _notify_crew(self):
        """Tell whoever is on the stand to bring the car up. A request that only
        appears on a board nobody is looking at is not a request."""
        self.ensure_one()
        if 'care.cafm.notification' not in self.env:
            return
        emps = self.env['care.valet.shift'].sudo().search(
            [('facility_id', '=', self.facility_id.id), ('state', '=', 'open')]
        ).mapped('employee_id')
        users = emps.mapped('user_id')
        if not users:
            users = self.env['res.users'].sudo().search(
                [('groups_id', 'in', self.env.ref('base.group_erp_manager').id)], limit=10)
        if not users:
            return
        where = self.spot_id.name or self.zone_id.name or ''
        try:
            self.env['care.cafm.notification'].sudo().push(
                users, _('🚗 Vehicle Retrieval Request'),
                '%s — %s%s' % (self.plate, self.name, (' · %s' % where) if where else ''),
                ntype='alert', action_url='/cafm/m/valet', record=self)
        except Exception:
            pass

    def action_deliver(self, by=None, fee=None, tip=None, paid=None):
        for t in self:
            vals = {'state': 'delivered', 'delivered_at': fields.Datetime.now()}
            if by:
                vals['delivered_by'] = by
            if fee is not None:
                vals['fee'] = fee
            if tip is not None:
                vals['tip'] = tip
            if paid is not None:
                vals['paid'] = paid
            t.write(vals)
            if t.spot_id:
                t.spot_id.write({'state': 'free', 'ticket_id': False})
            t.message_post(body=_('✅ The vehicle was handed over to the guest%s.')
                           % ((' within %d minutes' % t.retrieval_minutes) if t.retrieval_minutes else ''))

    def action_cancel(self):
        for t in self:
            if t.spot_id:
                t.spot_id.write({'state': 'free', 'ticket_id': False})
            t.write({'state': 'cancelled'})


class ValetShift(models.Model):
    """An attendant's shift — the takings and volume behind it."""
    _name = 'care.valet.shift'
    _description = 'Valet Shift'
    _order = 'start_at desc'

    name = fields.Char(string='Shift', default='/', copy=False, readonly=True)
    facility_id = fields.Many2one('care.cafm.facility', string='Facility', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    start_at = fields.Datetime(string='Start', default=fields.Datetime.now, required=True)
    end_at = fields.Datetime(string='End')
    ticket_ids = fields.One2many('care.valet.ticket', 'shift_id', string='Tickets')
    ticket_count = fields.Integer(compute='_compute_totals', store=True, string='Ticket Count')
    total_fees = fields.Float(compute='_compute_totals', store=True, string='Total Fees')
    total_tips = fields.Float(compute='_compute_totals', store=True, string='Total Tips')
    cash_due = fields.Float(compute='_compute_totals', store=True, string='Cash Due for Handover')
    state = fields.Selection([('open', 'Open'), ('closed', 'Closed')], default='open', required=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('ticket_ids.fee', 'ticket_ids.tip', 'ticket_ids.paid', 'ticket_ids.payment_method')
    def _compute_totals(self):
        for s in self:
            t = s.ticket_ids
            s.ticket_count = len(t)
            s.total_fees = sum(t.mapped('fee'))
            s.total_tips = sum(t.mapped('tip'))
            s.cash_due = sum(x.fee + x.tip for x in t if x.payment_method == 'cash' and x.paid)

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', '/') == '/':
                v['name'] = self.env['ir.sequence'].next_by_code('care.valet.shift') or '/'
        return super().create(vals_list)

    def action_close(self):
        self.write({'state': 'closed', 'end_at': fields.Datetime.now()})
