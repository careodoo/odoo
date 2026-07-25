# -*- coding: utf-8 -*-
"""Pool maintenance, where the readings are the service.

Nobody is paid to skim a pool. They are paid to keep the water inside a band,
and to be able to prove it afterwards. So the reading is the record everything
else hangs off: it decides whether the pool may stay open, it is what a health
inspector asks for, and a pool with no reading today is not a maintained pool.
"""
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Pool(models.Model):
    _name = 'care.pool.pool'
    _description = 'Pool'
    _inherit = ['mail.thread']
    _order = 'facility_id, name'

    name = fields.Char(string='Pool', required=True, tracking=True)
    name_en = fields.Char(string='English name')
    facility_id = fields.Many2one('care.cafm.facility', string='Facility', required=True,
                                  tracking=True, index=True)
    location_id = fields.Many2one('care.cafm.location', string='Location', tracking=True)
    pool_type = fields.Selection([
        ('swim', 'Swimming pool'), ('kids', 'Kids pool'), ('jacuzzi', 'Jacuzzi'),
        ('therapy', 'Therapy pool'), ('lap', 'Lap pool'),
    ], string='Type', default='swim', required=True, tracking=True)
    volume_m3 = fields.Float(string='Capacity (m³)', tracking=True)
    depth_min = fields.Float(string='Min depth (m)')
    depth_max = fields.Float(string='Max depth (m)')
    filter_type = fields.Selection([
        ('sand', 'Sand'), ('cartridge', 'Cartridge'), ('de', 'Diatomite (DE)'), ('other', 'Other'),
    ], string='Filter type', default='sand')
    treatment = fields.Selection([
        ('chlorine', 'Chlorine'), ('salt', 'Salt generator'), ('bromine', 'Bromine'), ('uv', 'UV'),
    ], string='Treatment method', default='chlorine')

    # The safe band. Defaults follow common public-pool practice, but a
    # therapy pool or a salt system legitimately sits elsewhere — so it is
    # per pool, not a constant buried in the code.
    ph_min = fields.Float(string='Min pH', default=7.2)
    ph_max = fields.Float(string='Max pH', default=7.8)
    cl_min = fields.Float(string='Min free chlorine (ppm)', default=1.0)
    cl_max = fields.Float(string='Max free chlorine (ppm)', default=3.0)
    temp_min = fields.Float(string='Min temperature (°C)', default=26.0)
    temp_max = fields.Float(string='Max temperature (°C)', default=29.0)
    turbidity_max = fields.Float(string='Max turbidity (NTU)', default=0.5)

    state = fields.Selection([
        ('open', 'Open'), ('closed', 'Closed'), ('maintenance', 'Under maintenance'),
    ], string='Status', default='open', required=True, tracking=True)
    closed_reason = fields.Char(string='Closure reason', tracking=True)
    reading_ids = fields.One2many('care.pool.reading', 'pool_id', string='Readings')
    task_ids = fields.One2many('care.pool.task', 'pool_id', string='Maintenance work')

    last_reading = fields.Datetime(string='Last reading', compute='_compute_last', store=True)
    last_safe = fields.Boolean(string='Last reading in range', compute='_compute_last', store=True)
    needs_reading = fields.Boolean(string='Awaiting a reading today', compute='_compute_needs',
                                   search='_search_needs')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('reading_ids.taken_at', 'reading_ids.is_safe')
    def _compute_last(self):
        for p in self:
            last = p.reading_ids.sorted('taken_at', reverse=True)[:1]
            p.last_reading = last.taken_at if last else False
            p.last_safe = last.is_safe if last else False

    def _compute_needs(self):
        today = fields.Date.context_today(self)
        for p in self:
            p.needs_reading = not (p.last_reading and
                                   fields.Datetime.context_timestamp(p, p.last_reading).date() == today)

    def _search_needs(self, operator, value):
        today = fields.Date.context_today(self)
        done = self.search([]).filtered(
            lambda p: p.last_reading and
            fields.Datetime.context_timestamp(p, p.last_reading).date() == today)
        op = 'not in' if (operator == '=') == bool(value) else 'in'
        return [('id', op, done.ids)]

    def action_close(self, reason=None):
        for p in self:
            p.write({'state': 'closed', 'closed_reason': reason or p.closed_reason})
            p.message_post(body=_('⛔ Pool closed: %s') % (reason or ''))

    def action_reopen(self):
        """Reopening needs a passing reading. Otherwise 'closed for chemistry'
        becomes a formality someone clicks past."""
        for p in self:
            last = p.reading_ids.sorted('taken_at', reverse=True)[:1]
            if not last or not last.is_safe:
                raise UserError(_('The pool cannot reopen before a reading inside the safe band is recorded.'))
            p.write({'state': 'open', 'closed_reason': False})
            p.message_post(body=_('✅ Pool reopened after a passing reading.'))

    @api.model
    def _cron_missing_reading(self):
        """A pool with no reading today is not a maintained pool — say so before
        the day ends, not in next month's report."""
        pools = self.search([('state', '=', 'open')]).filtered('needs_reading')
        if not pools or 'care.cafm.notification' not in self.env:
            return True
        for p in pools:
            users = self.env['care.cafm.client'].sudo().search(
                [('partner_id', '=', p.facility_id.partner_id.id)], limit=1).user_ids
            staff = self.env['res.users'].sudo().search(
                [('groups_id', 'in', self.env.ref('base.group_erp_manager').id)], limit=5)
            try:
                self.env['care.cafm.notification'].sudo().push(
                    (users | staff), _('🏊 No reading today'),
                    '%s — %s' % (p.name, p.facility_id.name or ''), ntype='warning', record=p)
            except Exception:
                pass
        return True


class PoolReading(models.Model):
    """One set of water numbers at one moment. This is the evidence."""
    _name = 'care.pool.reading'
    _description = 'Water reading'
    _inherit = ['mail.thread']
    _order = 'taken_at desc, id desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    pool_id = fields.Many2one('care.pool.pool', string='Pool', required=True,
                              ondelete='cascade', index=True, tracking=True)
    facility_id = fields.Many2one(related='pool_id.facility_id', store=True, index=True)
    taken_at = fields.Datetime(string='Taken at', default=fields.Datetime.now,
                               required=True, index=True, tracking=True)
    taken_by = fields.Many2one('hr.employee', string='Taken by', tracking=True)

    ph = fields.Float(string='pH', tracking=True)
    free_chlorine = fields.Float(string='Free chlorine (ppm)', tracking=True)
    combined_chlorine = fields.Float(string='Combined chlorine (ppm)',
                                     help='Above 0.5 means the water needs shock chlorination.')
    temperature = fields.Float(string='Temperature (°C)', tracking=True)
    turbidity = fields.Float(string='Turbidity (NTU)', tracking=True)
    alkalinity = fields.Float(string='Total alkalinity (ppm)')
    cyanuric_acid = fields.Float(string='Cyanuric acid (ppm)',
                                 help='The stabiliser — above 100 it weakens chlorine effectiveness.')

    is_safe = fields.Boolean(string='Within the safe band', compute='_compute_safe', store=True)
    breaches = fields.Char(string='Values out of range', compute='_compute_safe', store=True)
    action_taken = fields.Text(string='Action taken')
    closed_pool = fields.Boolean(string='Closed the pool', readonly=True)
    note = fields.Char(string='Note')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.pool.reading') or '/'
        recs = super().create(vals_list)
        recs._enforce_band()
        return recs

    @api.depends('ph', 'free_chlorine', 'temperature', 'turbidity', 'pool_id')
    def _compute_safe(self):
        for r in self:
            p = r.pool_id
            out = []
            if not p:
                r.is_safe, r.breaches = True, False
                continue
            if r.ph and not (p.ph_min <= r.ph <= p.ph_max):
                out.append('pH %.1f' % r.ph)
            if r.free_chlorine and not (p.cl_min <= r.free_chlorine <= p.cl_max):
                out.append(_('chlorine %.1f') % r.free_chlorine)
            if r.temperature and not (p.temp_min <= r.temperature <= p.temp_max):
                out.append(_('temperature %.1f') % r.temperature)
            if r.turbidity and r.turbidity > p.turbidity_max:
                out.append(_('turbidity %.2f') % r.turbidity)
            if r.combined_chlorine and r.combined_chlorine > 0.5:
                out.append(_('combined chlorine %.1f') % r.combined_chlorine)
            r.breaches = ' · '.join(out) or False
            r.is_safe = not out

    def _enforce_band(self):
        """A reading outside the band closes the pool. Leaving that to a human
        to notice is how a pool stays open on bad water."""
        for r in self:
            if r.is_safe or not r.pool_id:
                continue
            r.closed_pool = True
            r.pool_id.action_close(_('Reading out of range: %s') % (r.breaches or ''))
            if 'care.cafm.notification' in self.env:
                staff = self.env['res.users'].sudo().search(
                    [('groups_id', 'in', self.env.ref('base.group_erp_manager').id)], limit=8)
                try:
                    self.env['care.cafm.notification'].sudo().push(
                        staff, _('🏊 Pool closed — reading out of range'),
                        '%s: %s' % (r.pool_id.name, r.breaches or ''), ntype='alert', record=r)
                except Exception:
                    pass


class PoolTask(models.Model):
    """The physical work — backwashing, vacuuming, dosing. Kept apart from the
    reading because the reading is a measurement and this is a job done."""
    _name = 'care.pool.task'
    _description = 'Pool maintenance task'
    _inherit = ['mail.thread']
    _order = 'done_at desc, id desc'

    pool_id = fields.Many2one('care.pool.pool', string='Pool', required=True,
                              ondelete='cascade', index=True, tracking=True)
    facility_id = fields.Many2one(related='pool_id.facility_id', store=True, index=True)
    task_type = fields.Selection([
        ('backwash', 'Filter backwash'), ('vacuum', 'Vacuum the floor'),
        ('skim', 'Skim the surface'), ('brush', 'Brush walls and waterline'),
        ('basket', 'Empty the baskets'), ('filter_clean', 'Clean / replace filter'),
        ('dose', 'Dose chemicals'), ('shock', 'Shock chlorination'),
        ('drain', 'Drain and refill'), ('repair', 'Repair'),
    ], string='Task type', required=True, tracking=True)
    done_at = fields.Datetime(string='Done at', default=fields.Datetime.now, required=True, tracking=True)
    done_by = fields.Many2one('hr.employee', string='Done by', tracking=True)
    chemical = fields.Char(string='Chemical used', tracking=True)
    quantity = fields.Float(string='Quantity', tracking=True)
    uom_name = fields.Char(string='Unit', default='kg', tracking=True)
    filter_pressure = fields.Float(string='Filter pressure (bar)',
                                   help='Half a bar above normal means it is time to backwash.', tracking=True)
    note = fields.Char(string='Note', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
