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
    # ---- planning, not just recording -----------------------------------
    # The round carried only done_by — who performed it, filled in afterwards.
    # There was no way to say "disinfect ICU at 18:00 and give it to Ahmed",
    # so the service could describe the past but never direct the present.
    assigned_to = fields.Many2one('hr.employee', string='Assigned to',
                                  tracking=True, index=True)
    assigned_team_id = fields.Many2one('care.cafm.team', string='Assigned team',
                                       tracking=True)
    planned_at = fields.Datetime(string='Planned for', tracking=True, index=True)
    priority = fields.Selection([
        ('routine', 'Routine'), ('urgent', 'Urgent'),
        ('outbreak', 'Outbreak — immediate'),
    ], string='Priority', default='routine', required=True, tracking=True)
    is_overdue = fields.Boolean(string='Overdue', compute='_compute_overdue',
                                search='_search_overdue')
    minutes_late = fields.Integer(string='Late by (minutes)',
                                  compute='_compute_overdue')

    # ---- when the space can be used again --------------------------------
    # The contact time is enforced already, but nobody downstream was told
    # when the room reopens. A ward waiting on a cleared room needs that
    # number more than it needs the round record.
    reentry_at = fields.Datetime(string='Safe to re-enter at',
                                 compute='_compute_reentry', store=True)
    reentry_minutes_left = fields.Integer(string='Re-entry in (minutes)',
                                          compute='_compute_reentry_left')

    @api.depends('done_at', 'contact_minutes', 'product_id.contact_minutes', 'state')
    def _compute_reentry(self):
        for r in self:
            if r.state != 'done' or not r.done_at:
                r.reentry_at = False
                continue
            # The surface is only safe once the longest dwell has elapsed —
            # the applied time, or the product requirement if it is longer.
            mins = max(r.contact_minutes or 0, r.product_id.contact_minutes or 0)
            r.reentry_at = r.done_at + timedelta(minutes=mins)

    def _compute_reentry_left(self):
        now = fields.Datetime.now()
        for r in self:
            r.reentry_minutes_left = int(
                (r.reentry_at - now).total_seconds() / 60) if r.reentry_at and r.reentry_at > now else 0

    def _compute_overdue(self):
        now = fields.Datetime.now()
        for r in self:
            late = bool(r.planned_at and r.state in ('draft', 'assigned')
                        and r.planned_at < now)
            r.is_overdue = late
            r.minutes_late = int((now - r.planned_at).total_seconds() / 60) if late else 0

    def _search_overdue(self, operator, value):
        now = fields.Datetime.now()
        dom = [('planned_at', '<', now), ('state', 'in', ('draft', 'assigned'))]
        if (operator == '=') != bool(value):
            return ['!'] + dom
        return dom

    def action_assign(self):
        """Hand the round to someone, and tell them."""
        for r in self:
            if not (r.assigned_to or r.assigned_team_id):
                raise UserError(_('Choose a worker or a team to assign this round to.'))
            r.state = 'assigned'
            if 'care.cafm.notification' in self.env and r.assigned_to.user_id:
                try:
                    self.env['care.cafm.notification'].sudo().push(
                        r.assigned_to.user_id,
                        _('🧴 A disinfection round is assigned to you'),
                        '%s — %s' % (r.location_id.name or r.facility_id.name or '',
                                     str(r.planned_at or '')[:16]),
                        ntype='task')
                except Exception:
                    pass
        return True

    def action_start(self):
        for r in self:
            if r.state not in ('draft', 'assigned'):
                raise UserError(_('Only an assigned round can be started.'))
            r.write({'state': 'in_progress',
                     'done_by': r.done_by.id or r.assigned_to.id})
        return True

    @api.model
    def _cron_overdue(self):
        """Chase what was planned and never happened. An outbreak round left
        sitting is the one that matters most."""
        late = self.search([('is_overdue', '=', True)])
        for r in late:
            if r.assigned_to.user_id and 'care.cafm.notification' in self.env:
                try:
                    self.env['care.cafm.notification'].sudo().push(
                        r.assigned_to.user_id,
                        _('⏰ A disinfection round is overdue'),
                        '%s — %s minutes late' % (
                            r.location_id.name or '', r.minutes_late),
                        ntype='alert' if r.priority != 'routine' else 'warning')
                except Exception:
                    pass
        return len(late)


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
        ('draft', 'Draft'), ('assigned', 'Assigned'), ('in_progress', 'In progress'),
        ('done', 'Completed'), ('rework', 'Needs redoing'),
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
