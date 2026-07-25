# -*- coding: utf-8 -*-
"""Pest control as the trade actually runs it.

A pest programme is not a series of work orders. It is a standing schedule of
visits against a fixed grid of numbered stations, a register of what may legally
be applied and at what dilution, and a record — per station, per visit — of what
was caught. The client's questions are always the same three: when were you last
here, what did you find, and what did you spray near my kitchen.
"""
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

PEST_TYPES = [
    ('cockroach', 'Cockroaches'), ('rodent', 'Rodents'), ('ant', 'Ants'),
    ('fly', 'Flies'), ('mosquito', 'Mosquitoes'), ('bedbug', 'Bed Bugs'),
    ('termite', 'Termites'), ('bird', 'Birds'), ('snake', 'Reptiles'),
    ('other', 'Other'),
]


class PestChemical(models.Model):
    """The approved-pesticide register. A client is entitled to ask what was
    sprayed near their kitchen and to be told the registration number."""
    _name = 'care.pest.chemical'
    _description = 'Approved Pesticide'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='Trade Name', required=True, tracking=True)
    name_en = fields.Char(string='English Name')
    active_ingredient = fields.Char(string='Active Ingredient', required=True, tracking=True)
    moh_registration = fields.Char(string='Ministry of Health Registration Number', tracking=True,
                                   help='Unregistered pesticides must not be used.')
    formulation = fields.Selection([
        ('sc', 'Suspension Concentrate (SC)'), ('ec', 'Emulsifiable Concentrate (EC)'), ('wp', 'Wettable Powder (WP)'),
        ('gel', 'Bait Gel'), ('bait', 'Granular Bait'), ('dust', 'Dust'),
        ('aerosol', 'Spray'), ('other', 'Other'),
    ], string='Formulation', default='sc', tracking=True)
    target_pests = fields.Char(string='Target Pests')
    dilution = fields.Char(string='Dilution Rate', help='Example: 5 ml per litre of water.')
    reentry_hours = fields.Integer(string='Re-entry Interval (hours)', default=4, tracking=True,
                                   help='Number of hours the area must remain unoccupied after treatment.')
    food_area_safe = fields.Boolean(string='Approved for Food Areas', tracking=True)
    hazard_note = fields.Text(string='Safety Warnings')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def name_get(self):
        return [(r.id, '%s (%s)' % (r.name, r.active_ingredient or '')) for r in self]


class PestStation(models.Model):
    """A numbered station on the grid. The grid is the service — a client pays
    for coverage, and coverage is only demonstrable station by station."""
    _name = 'care.pest.station'
    _description = 'Control Station'
    _inherit = ['mail.thread']
    _order = 'facility_id, code'

    name = fields.Char(string='Name', compute='_compute_name', store=True)
    code = fields.Char(string='Station Number', required=True, tracking=True,
                       help='Number printed on the station itself so it can be matched in the field.')
    facility_id = fields.Many2one('care.cafm.facility', string='Facility', required=True,
                                  tracking=True, index=True)
    location_id = fields.Many2one('care.cafm.location', string='Location', tracking=True)
    station_type = fields.Selection([
        ('bait_station', 'Rodent Bait Station'), ('snap_trap', 'Snap Trap'),
        ('glue_board', 'Glue Board'), ('light_trap', 'Insect Light Trap'),
        ('pheromone', 'Pheromone Trap'), ('monitor', 'Monitoring Point'),
    ], string='Type', default='bait_station', required=True, tracking=True)
    target = fields.Selection(PEST_TYPES, string='Target Pest', default='rodent')
    indoor = fields.Boolean(string='Indoor', default=True)
    installed_on = fields.Date(string='Installation Date', default=fields.Date.context_today)
    state = fields.Selection([
        ('active', 'Active'), ('damaged', 'Damaged'), ('missing', 'Missing'),
        ('removed', 'Removed'),
    ], string='Status', default='active', required=True, tracking=True)
    note = fields.Char(string='Note')
    last_check = fields.Date(string='Last Inspection', compute='_compute_last', store=True)
    last_catch = fields.Integer(string='Last Catch Count', compute='_compute_last', store=True)
    check_ids = fields.One2many('care.pest.visit.station', 'station_id', string='Inspections')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [('code_facility_uniq', 'unique(code, facility_id)',
                         'This station number is already used in this facility.')]

    @api.depends('code', 'station_type')
    def _compute_name(self):
        types = dict(self._fields['station_type'].selection)
        for r in self:
            r.name = '%s — %s' % (r.code or '', types.get(r.station_type, ''))

    @api.depends('check_ids.visit_id.visit_date', 'check_ids.catch_count')
    def _compute_last(self):
        for r in self:
            checks = r.check_ids.filtered(lambda c: c.visit_id.visit_date).sorted(
                lambda c: c.visit_id.visit_date, reverse=True)
            r.last_check = checks[:1].visit_id.visit_date if checks else False
            r.last_catch = checks[:1].catch_count if checks else 0


class PestProgram(models.Model):
    """The standing schedule. Treatment does not wait for a sighting — that is
    the whole difference between a programme and a call-out."""
    _name = 'care.pest.program'
    _description = 'Control Programme'
    _inherit = ['mail.thread']
    _order = 'facility_id, name'

    name = fields.Char(string='Programme', required=True, tracking=True)
    facility_id = fields.Many2one('care.cafm.facility', string='Facility', required=True,
                                  tracking=True, index=True)
    frequency = fields.Selection([
        ('weekly', 'Weekly'), ('biweekly', 'Fortnightly'), ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ], string='Frequency', default='monthly', required=True, tracking=True)
    targets = fields.Char(string='Covered Pests')
    technician_id = fields.Many2one('hr.employee', string='Assigned Technician', tracking=True)
    start_date = fields.Date(string='Programme Start', default=fields.Date.context_today)
    next_due = fields.Date(string='Next Visit', tracking=True, index=True)
    last_visit = fields.Date(string='Last Visit', compute='_compute_visits', store=True)
    visit_count = fields.Integer(string='Visit Count', compute='_compute_visits')
    visit_ids = fields.One2many('care.pest.visit', 'program_id', string='Visits')
    is_overdue = fields.Boolean(string='Overdue', compute='_compute_overdue', store=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    DAYS = {'weekly': 7, 'biweekly': 14, 'monthly': 30, 'quarterly': 90}

    @api.depends('visit_ids.visit_date', 'visit_ids.state')
    def _compute_visits(self):
        for r in self:
            done = r.visit_ids.filtered(lambda v: v.state == 'done' and v.visit_date)
            r.last_visit = max(done.mapped('visit_date')) if done else False
            r.visit_count = len(r.visit_ids)

    @api.depends('next_due')
    def _compute_overdue(self):
        today = fields.Date.context_today(self)
        for r in self:
            r.is_overdue = bool(r.next_due and r.next_due < today)

    def action_log_visit(self):
        """Open a fresh visit pre-loaded with this facility's whole station grid,
        because a visit that skips stations is not a visit."""
        self.ensure_one()
        stations = self.env['care.pest.station'].search(
            [('facility_id', '=', self.facility_id.id), ('state', '=', 'active')])
        visit = self.env['care.pest.visit'].create({
            'program_id': self.id, 'facility_id': self.facility_id.id,
            'technician_id': self.technician_id.id,
            'station_line_ids': [(0, 0, {'station_id': s.id}) for s in stations],
        })
        return {'type': 'ir.actions.act_window', 'res_model': 'care.pest.visit',
                'res_id': visit.id, 'view_mode': 'form'}

    def _roll_next(self, from_date=None):
        self.ensure_one()
        base = from_date or fields.Date.context_today(self)
        self.next_due = base + timedelta(days=self.DAYS.get(self.frequency, 30))

    @api.model
    def _cron_due_reminder(self):
        """Warn the crew before a programme lapses, not after."""
        today = fields.Date.context_today(self)
        soon = today + timedelta(days=2)
        due = self.search([('next_due', '!=', False), ('next_due', '<=', soon)])
        if not due or 'care.cafm.notification' not in self.env:
            return
        for p in due:
            users = p.technician_id.user_id
            if not users:
                continue
            late = p.next_due < today
            self.env['care.cafm.notification'].sudo().push(
                users,
                _('🐜 Pest Control Visit %s') % (_('Overdue') if late else _('Due')),
                '%s — %s' % (p.name, p.facility_id.name or ''),
                ntype='alert' if late else 'task', record=p)
        return True


class PestVisit(models.Model):
    _name = 'care.pest.visit'
    _description = 'Pest Control Visit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'visit_date desc, id desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    program_id = fields.Many2one('care.pest.program', string='Programme', index=True)
    facility_id = fields.Many2one('care.cafm.facility', string='Facility', required=True,
                                  tracking=True, index=True)
    visit_date = fields.Date(string='Visit Date', default=fields.Date.context_today,
                             required=True, tracking=True, index=True)
    technician_id = fields.Many2one('hr.employee', string='Technician', tracking=True)
    visit_type = fields.Selection([
        ('routine', 'Scheduled Visit'), ('callout', 'Emergency Call-out'),
        ('followup', 'Follow-up Visit'),
    ], string='Visit Type', default='routine', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'), ('done', 'Completed'), ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    station_line_ids = fields.One2many('care.pest.visit.station', 'visit_id',
                                       string='Inspected Stations')
    chemical_line_ids = fields.One2many('care.pest.visit.chemical', 'visit_id',
                                        string='Products Applied')
    findings = fields.Text(string='Notes and Recommendations')
    stations_checked = fields.Integer(string='Stations Inspected', compute='_compute_totals', store=True)
    total_catch = fields.Integer(string='Total Catch', compute='_compute_totals', store=True)
    activity_level = fields.Selection([
        ('none', 'No Activity'), ('low', 'Light Activity'), ('medium', 'Moderate Activity'),
        ('high', 'High Activity'),
    ], string='Activity Level', compute='_compute_totals', store=True)
    reentry_until = fields.Datetime(string='Re-entry Allowed After', compute='_compute_reentry',
                                    store=True,
                                    help='The longest re-entry interval among the products applied.')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.pest.visit') or '/'
        return super().create(vals_list)

    @api.depends('station_line_ids.checked', 'station_line_ids.catch_count')
    def _compute_totals(self):
        for v in self:
            checked = v.station_line_ids.filtered('checked')
            v.stations_checked = len(checked)
            v.total_catch = sum(checked.mapped('catch_count'))
            n = v.total_catch
            v.activity_level = ('none' if n == 0 else 'low' if n <= 3
                                else 'medium' if n <= 10 else 'high')

    @api.depends('chemical_line_ids.chemical_id', 'visit_date')
    def _compute_reentry(self):
        for v in self:
            hours = max(v.chemical_line_ids.mapped('chemical_id.reentry_hours') or [0])
            if hours and v.visit_date:
                v.reentry_until = fields.Datetime.to_datetime(v.visit_date) + timedelta(hours=hours)
            else:
                v.reentry_until = False

    def action_done(self):
        for v in self:
            if not v.station_line_ids.filtered('checked'):
                raise UserError(_('Record at least one station inspection before completing the visit.'))
            v.state = 'done'
            if v.program_id:
                v.program_id._roll_next(v.visit_date)
            v._notify_client()

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def _notify_client(self):
        """Tell the client what happened — the report is the service."""
        self.ensure_one()
        if 'care.cafm.notification' not in self.env:
            return
        client = self.env['care.cafm.client'].sudo().search(
            [('partner_id', '=', self.facility_id.partner_id.id)], limit=1)
        users = client.user_ids if client else self.env['res.users']
        if not users:
            return
        lvl = dict(self._fields['activity_level'].selection).get(self.activity_level, '')
        try:
            self.env['care.cafm.notification'].sudo().push(
                users, _('🐜 Pest Control Visit Completed'),
                '%s — %s stations · %s' % (self.facility_id.name or '', self.stations_checked, lvl),
                ntype='info', record=self)
        except Exception:
            pass


class PestVisitStation(models.Model):
    """What one station showed on one visit. This line is the evidence."""
    _name = 'care.pest.visit.station'
    _description = 'Station Inspection'
    _order = 'id'

    visit_id = fields.Many2one('care.pest.visit', required=True, ondelete='cascade', index=True)
    station_id = fields.Many2one('care.pest.station', string='Station', required=True, index=True)
    checked = fields.Boolean(string='Inspected', default=True)
    catch_count = fields.Integer(string='Catch Count')
    bait_state = fields.Selection([
        ('intact', 'Intact'), ('partial', 'Partially Consumed'), ('consumed', 'Fully Consumed'),
        ('missing', 'Missing'), ('replaced', 'Replaced'),
    ], string='Bait Condition', default='intact')
    station_state = fields.Selection([
        ('ok', 'Intact'), ('damaged', 'Damaged'), ('missing', 'Missing'), ('blocked', 'Inaccessible'),
    ], string='Station Condition', default='ok')
    note = fields.Char(string='Note')
    facility_id = fields.Many2one(related='visit_id.facility_id', store=True, index=True)
    visit_date = fields.Date(related='visit_id.visit_date', store=True, index=True)

    @api.onchange('station_state')
    def _onchange_station_state(self):
        """A station reported damaged or missing on a visit should not stay
        'active' on the grid — the next visit would count it as covered."""
        for l in self:
            if l.station_state in ('damaged', 'missing') and l.station_id:
                l.station_id.state = l.station_state


class PestVisitChemical(models.Model):
    _name = 'care.pest.visit.chemical'
    _description = 'Product Applied'
    _order = 'id'

    visit_id = fields.Many2one('care.pest.visit', required=True, ondelete='cascade', index=True)
    chemical_id = fields.Many2one('care.pest.chemical', string='Pesticide', required=True)
    area = fields.Char(string='Treated Area')
    quantity = fields.Float(string='Quantity Used')
    uom_name = fields.Char(string='Unit', default='Litres of Solution')
    dilution_used = fields.Char(string='Dilution Applied')
    active_ingredient = fields.Char(related='chemical_id.active_ingredient', string='Active Ingredient')
    reentry_hours = fields.Integer(related='chemical_id.reentry_hours', string='Re-entry Interval (hours)')


class PestSighting(models.Model):
    """A client-reported sighting. It is not a work order — it is a data point
    that should pull the next visit forward."""
    _name = 'care.pest.sighting'
    _description = 'Pest Sighting Report'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    facility_id = fields.Many2one('care.cafm.facility', string='Facility', required=True, index=True)
    location_id = fields.Many2one('care.cafm.location', string='Location')
    pest_type = fields.Selection(PEST_TYPES, string='Pest Type', required=True, tracking=True)
    severity = fields.Selection([
        ('one', 'Single Sighting'), ('few', 'Multiple Sightings'), ('infestation', 'Visible Infestation'),
    ], string='Extent of Infestation', default='one', required=True, tracking=True)
    description = fields.Text(string='Description')
    reported_by = fields.Many2one('res.users', string='Reported By', default=lambda s: s.env.user)
    state = fields.Selection([
        ('new', 'New'), ('scheduled', 'Visit Scheduled'), ('treated', 'Treated'),
        ('closed', 'Closed'),
    ], string='Status', default='new', required=True, tracking=True)
    visit_id = fields.Many2one('care.pest.visit', string='Treatment Visit', readonly=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.pest.sighting') or '/'
        recs = super().create(vals_list)
        recs._alert_crew()
        return recs

    def _alert_crew(self):
        if 'care.cafm.notification' not in self.env:
            return
        for r in self:
            prog = self.env['care.pest.program'].sudo().search(
                [('facility_id', '=', r.facility_id.id)], limit=1)
            users = prog.technician_id.user_id if prog else self.env['res.users']
            if not users:
                continue
            try:
                self.env['care.cafm.notification'].sudo().push(
                    users, _('🐜 Pest Sighting Report'),
                    '%s — %s · %s' % (
                        r.facility_id.name or '',
                        dict(self._fields['pest_type'].selection).get(r.pest_type, ''),
                        dict(self._fields['severity'].selection).get(r.severity, '')),
                    ntype='alert' if r.severity == 'infestation' else 'task')
            except Exception:
                pass

    def action_schedule(self):
        """Pull the programme's next visit forward to tomorrow."""
        for r in self:
            prog = self.env['care.pest.program'].sudo().search(
                [('facility_id', '=', r.facility_id.id)], limit=1)
            if prog:
                prog.next_due = fields.Date.context_today(self) + timedelta(days=1)
            r.state = 'scheduled'
