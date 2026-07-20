# -*- coding: utf-8 -*-
"""Disinfection, where the contact time is the service.

Wiping a surface with disinfectant and drying it immediately does nothing —
the product has to sit for its dwell time to kill anything. That single number
is what separates disinfection from wiping, and it is the one thing nobody
records. So it is a required field here, checked against the product's own
requirement, and a round that did not observe it is marked as such rather than
quietly counted as done.
"""
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DisinfectProduct(models.Model):
    _name = 'care.disinfect.product'
    _description = 'Approved disinfectant'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='Trade name', required=True, tracking=True)
    name_en = fields.Char(string='English name')
    active_ingredient = fields.Char(string='Active ingredient', required=True, tracking=True)
    registration = fields.Char(string='Registration number', tracking=True)
    dilution = fields.Char(string='Approved dilution')
    contact_minutes = fields.Integer(string='Required contact time (minutes)', default=1,
                                     required=True, tracking=True,
                                     help='How long the disinfectant must stay wet on the surface.')
    surfaces = fields.Char(string='Suitable surfaces')
    food_safe = fields.Boolean(string='Food-area safe')
    ppe_note = fields.Char(string='Required PPE')
    hazard_note = fields.Text(string='Warnings')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def name_get(self):
        return [(r.id, '%s (%s)' % (r.name, r.active_ingredient or '')) for r in self]


class DisinfectRound(models.Model):
    _name = 'care.disinfect.round'
    _description = 'Disinfection round'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'done_at desc, id desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    facility_id = fields.Many2one('care.cafm.facility', string='Facility', required=True,
                                  tracking=True, index=True)
    location_id = fields.Many2one('care.cafm.location', string='Location', tracking=True)
    round_type = fields.Selection([
        ('routine', 'Routine'), ('terminal', 'Terminal (after discharge)'),
        ('outbreak', 'Outbreak response'), ('preventive', 'Scheduled preventive'),
    ], string='Round type', default='routine', required=True, tracking=True)
    method = fields.Selection([
        ('wipe', 'Wipe'), ('spray', 'Spray'), ('fog', 'Fogging'),
        ('uv', 'UV'), ('electrostatic', 'Electrostatic spray'),
    ], string='Method', default='wipe', required=True, tracking=True)
    done_at = fields.Datetime(string='Done at', default=fields.Datetime.now,
                              required=True, index=True, tracking=True)
    done_by = fields.Many2one('hr.employee', string='Done by', tracking=True)
    product_id = fields.Many2one('care.disinfect.product', string='Disinfectant used',
                                 required=True, tracking=True)
    dilution_used = fields.Char(string='Dilution used')
    contact_minutes = fields.Integer(string='Contact time applied (minutes)', required=True,
                                     default=1, tracking=True)
    required_minutes = fields.Integer(related='product_id.contact_minutes',
                                      string='Required (minutes)')
    contact_ok = fields.Boolean(string='Contact time observed', compute='_compute_contact',
                                store=True)

    # the surfaces that actually matter
    hit_handles = fields.Boolean(string='Handles and buttons')
    hit_rails = fields.Boolean(string='Edges and rails')
    hit_switches = fields.Boolean(string='Switches and panels')
    hit_equipment = fields.Boolean(string='Non-critical equipment')
    hit_sanitary = fields.Boolean(string='Sanitary fittings')
    fresh_cloth = fields.Boolean(string='Fresh cloth per room', default=True,
                                 help='Reusing a cloth spreads contamination instead of removing it.')
    ventilated = fields.Boolean(string='Ventilated before reopening')

    atp_tested = fields.Boolean(string='ATP swab taken')
    atp_reading = fields.Integer(string='ATP reading (RLU)',
                                 help='Under 100 units counts as clean in a healthcare setting.')
    atp_pass = fields.Boolean(string='Passed the ATP swab', compute='_compute_atp', store=True)

    state = fields.Selection([
        ('draft', 'Draft'), ('done', 'Completed'), ('rework', 'Needs redoing'),
    ], string='Status', default='draft', required=True, tracking=True)
    note = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    SURFACES = ['hit_handles', 'hit_rails', 'hit_switches', 'hit_equipment', 'hit_sanitary']

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.disinfect.round') or '/'
        return super().create(vals_list)

    @api.depends('contact_minutes', 'product_id.contact_minutes')
    def _compute_contact(self):
        for r in self:
            need = r.product_id.contact_minutes or 0
            r.contact_ok = bool(r.contact_minutes and r.contact_minutes >= need)

    @api.depends('atp_tested', 'atp_reading')
    def _compute_atp(self):
        for r in self:
            r.atp_pass = bool(r.atp_tested and r.atp_reading and r.atp_reading < 100)

    @api.onchange('product_id')
    def _onchange_product(self):
        """Default the dwell time to what the product actually requires, so the
        common case is right and a shorter time is a deliberate entry."""
        for r in self:
            if r.product_id:
                r.contact_minutes = r.product_id.contact_minutes
                r.dilution_used = r.product_id.dilution

    def action_done(self):
        for r in self:
            if not any(r[f] for f in self.SURFACES):
                raise UserError(_('Mark which surfaces were disinfected.'))
            if not r.contact_ok:
                # not a hard block — it is a fact about this round that must
                # survive into the record instead of being argued about later
                r.state = 'rework'
                r.message_post(body=_(
                    '⚠️ Contact time of %s minutes is below the required %s — the round needs redoing.')
                    % (r.contact_minutes, r.required_minutes))
                continue
            if r.atp_tested and not r.atp_pass:
                r.state = 'rework'
                r.message_post(body=_('⚠️ ATP swab of %s RLU is above the limit — the round needs redoing.')
                               % r.atp_reading)
                continue
            r.state = 'done'

    def action_reset(self):
        self.write({'state': 'draft'})
