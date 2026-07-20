# -*- coding: utf-8 -*-
"""Material handling — moving things, and proving they arrived intact.

A hospital moves a CT scanner between floors, a mall relocates a tenant's
fit-out, a warehouse shifts pallets before an audit. The job is not "someone
carried it" — it is: what, from where to where, by whom, with what equipment,
and did it arrive without a scratch. The last part is where handling jobs go
wrong and where the argument happens afterwards, so condition-in and
condition-out with photos are the centre of the record, not an afterthought.
"""
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HandlingEquipment(models.Model):
    """A trolley, a forklift, a pallet jack, a crane. What the crew uses."""
    _name = 'care.handling.equipment'
    _description = 'Handling Equipment'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='Equipment', required=True, translate=True, tracking=True)
    code = fields.Char(string='Code', tracking=True)
    kind = fields.Selection([
        ('trolley', 'Trolley / cart'), ('pallet_jack', 'Pallet jack'),
        ('forklift', 'Forklift'), ('crane', 'Crane / hoist'),
        ('dolly', 'Dolly'), ('straps', 'Straps & rigging'), ('other', 'Other'),
    ], string='Type', default='trolley', required=True, tracking=True)
    capacity_kg = fields.Float(string='Capacity (kg)', tracking=True)
    facility_id = fields.Many2one('care.cafm.facility', string='Facility', index=True)
    needs_operator = fields.Boolean(string='Requires certified operator',
                                    help='A forklift or crane may only be used '
                                         'by a certified operator.')
    available = fields.Boolean(string='Available', default=True, tracking=True)
    nfc_uid = fields.Char(string='NFC tag', copy=False, index=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)


class HandlingJob(models.Model):
    """One move, from request to signed delivery."""
    _name = 'care.handling.job'
    _description = 'Handling Job'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'requested_at desc, id desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    facility_id = fields.Many2one('care.cafm.facility', string='Facility',
                                  required=True, index=True, tracking=True)
    move_type = fields.Selection([
        ('internal', 'Internal move'), ('delivery', 'Delivery in'),
        ('dispatch', 'Dispatch out'), ('relocation', 'Relocation / fit-out'),
        ('setup', 'Event setup / teardown'), ('disposal', 'Disposal move'),
    ], string='Move type', default='internal', required=True, tracking=True)
    cargo = fields.Char(string='What is being moved', required=True, tracking=True)
    cargo_category = fields.Selection([
        ('furniture', 'Furniture'), ('equipment', 'Equipment / machinery'),
        ('medical', 'Medical equipment'), ('it', 'IT / electronics'),
        ('documents', 'Documents / archives'), ('stock', 'Stock / pallets'),
        ('fragile', 'Fragile / high value'), ('other', 'Other'),
    ], string='Category', default='equipment', required=True, tracking=True)
    quantity = fields.Integer(string='Items / pieces', default=1)
    weight_kg = fields.Float(string='Weight (kg)')
    fragile = fields.Boolean(string='Fragile / handle with care', tracking=True)

    from_location_id = fields.Many2one('care.cafm.location', string='From',
                                       tracking=True)
    to_location_id = fields.Many2one('care.cafm.location', string='To',
                                     tracking=True)
    from_text = fields.Char(string='From (free text)')
    to_text = fields.Char(string='To (free text)')

    requested_by = fields.Many2one('res.users', string='Requested by',
                                   default=lambda s: s.env.user, tracking=True)
    requested_at = fields.Datetime(string='Requested at',
                                   default=fields.Datetime.now, tracking=True)
    scheduled_at = fields.Datetime(string='Scheduled for', tracking=True)
    priority = fields.Selection([
        ('normal', 'Normal'), ('urgent', 'Urgent'), ('critical', 'Critical'),
    ], string='Priority', default='normal', required=True, tracking=True)

    crew_lead_id = fields.Many2one('hr.employee', string='Crew lead', tracking=True)
    crew_ids = fields.Many2many('hr.employee', 'handling_job_crew_rel',
                                'job_id', 'emp_id', string='Crew')
    team_id = fields.Many2one('care.cafm.team', string='Team', tracking=True)
    equipment_ids = fields.Many2many('care.handling.equipment',
                                     string='Equipment used')

    state = fields.Selection([
        ('draft', 'Requested'), ('scheduled', 'Scheduled'),
        ('in_progress', 'In progress'), ('delivered', 'Delivered'),
        ('verified', 'Verified'), ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    started_at = fields.Datetime(string='Started', readonly=True)
    delivered_at = fields.Datetime(string='Delivered', readonly=True)
    duration_minutes = fields.Integer(string='Duration (minutes)',
                                      compute='_compute_duration', store=True)

    # ---- the point: condition before and after -------------------------
    condition_in = fields.Selection([
        ('good', 'Good'), ('minor', 'Minor marks noted'), ('damaged', 'Damaged'),
    ], string='Condition at pickup', tracking=True)
    condition_out = fields.Selection([
        ('good', 'Good'), ('minor', 'Minor marks'), ('damaged', 'Damaged in transit'),
    ], string='Condition at delivery', tracking=True)
    damage_note = fields.Text(string='Damage / handling notes')
    photo_in = fields.Binary(string='Photo at pickup', attachment=True)
    photo_out = fields.Binary(string='Photo at delivery', attachment=True)
    damaged = fields.Boolean(string='Damage recorded', compute='_compute_damaged',
                             store=True)

    # ---- proof of delivery ---------------------------------------------
    received_by = fields.Char(string='Received by (name)', tracking=True)
    signature = fields.Binary(string='Recipient signature', attachment=True)
    workorder_id = fields.Many2one('care.cafm.workorder', string='Work order',
                                   readonly=True, copy=False)
    note = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'care.handling.job') or '/'
        return super().create(vals_list)

    @api.depends('started_at', 'delivered_at')
    def _compute_duration(self):
        for j in self:
            j.duration_minutes = int(
                (j.delivered_at - j.started_at).total_seconds() / 60) \
                if j.started_at and j.delivered_at else 0

    @api.depends('condition_out')
    def _compute_damaged(self):
        for j in self:
            j.damaged = j.condition_out == 'damaged'

    def action_schedule(self):
        for j in self:
            if not j.scheduled_at:
                raise UserError(_('Set a scheduled time first.'))
            j.state = 'scheduled'

    def action_start(self):
        for j in self:
            # A move that starts without a recorded pickup condition is a move
            # that cannot prove anything if the cargo is damaged in transit.
            if not j.condition_in:
                raise UserError(_(
                    'Record the condition at pickup before starting — it is '
                    'the only baseline a damage claim can be measured against.'))
            j.write({'state': 'in_progress',
                     'started_at': fields.Datetime.now()})

    def action_deliver(self):
        for j in self:
            if not j.condition_out:
                raise UserError(_('Record the condition at delivery.'))
            if not j.received_by:
                raise UserError(_('Who received it? A delivery with no '
                                  'recipient is not proof of anything.'))
            j.write({'state': 'delivered', 'delivered_at': fields.Datetime.now()})
            if j.damaged:
                j.message_post(body=_('⚠️ Delivered with damage recorded in transit.'))

    def action_verify(self):
        self.write({'state': 'verified'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_to_workorder(self):
        """A damaged item needs a repair job — raise it from here."""
        self.ensure_one()
        if self.workorder_id:
            raise UserError(_('A work order was already raised.'))
        svc = self.env['care.cafm.service'].sudo().search(
            [('service_type', '=', 'maintenance')], limit=1) or \
            self.env['care.cafm.service'].sudo().search([], limit=1)
        wo = self.env['care.cafm.workorder'].sudo().create({
            'title': _('Damage from handling %s: %s') % (self.name, self.cargo),
            'description': self.damage_note or '',
            'facility_id': self.facility_id.id,
            'service_id': svc.id if svc else False,
            'priority': '2',
        })
        self.workorder_id = wo.id
        return wo
