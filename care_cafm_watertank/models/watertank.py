# -*- coding: utf-8 -*-
"""Water tank cleaning, which is a compliance record before it is a job.

Nobody inspects a clean tank. They inspect the paperwork: when was it last
done, by whom, with what, and what did the lab say about the water afterwards.
So the cleaning record carries its own certificate number and lab result, and
the next due date is derived from the last completed clean rather than typed in
and forgotten.
"""
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WaterTank(models.Model):
    _name = 'care.tank.tank'
    _description = 'Water tank'
    _inherit = ['mail.thread']
    _order = 'facility_id, code'

    name = fields.Char(string='Tank', compute='_compute_name', store=True)
    code = fields.Char(string='Tank number', required=True, tracking=True)
    facility_id = fields.Many2one('care.cafm.facility', string='Facility', required=True,
                                  tracking=True, index=True)
    location_id = fields.Many2one('care.cafm.location', string='Location', tracking=True)
    position = fields.Selection([
        ('roof', 'Roof'), ('ground', 'Ground'), ('underground', 'Underground'),
    ], string='Location', default='roof', required=True, tracking=True)
    material = fields.Selection([
        ('grp', 'GRP fibreglass'), ('polyethylene', 'Polyethylene'),
        ('concrete', 'Concrete'), ('steel', 'Galvanised steel'), ('stainless', 'Stainless steel'),
    ], string='Material', default='grp', tracking=True)
    capacity_gal = fields.Float(string='Capacity (gallons)', tracking=True)
    use = fields.Selection([
        ('potable', 'Potable'), ('domestic', 'Domestic'), ('fire', 'Firefighting'),
        ('irrigation', 'Irrigation'),
    ], string='Use', default='domestic', required=True, tracking=True)
    cycle_months = fields.Integer(string='Cleaning cycle (months)', default=6, required=True,
                                  tracking=True,
                                  help='Six months is the norm for potable water.')

    cleaning_ids = fields.One2many('care.tank.cleaning', 'tank_id', string='Cleaning operations')
    last_cleaned = fields.Date(string='Last cleaned', compute='_compute_cycle', store=True)
    next_due = fields.Date(string='Next due', compute='_compute_cycle', store=True, index=True)
    days_left = fields.Integer(string='Days left', compute='_compute_days')
    status = fields.Selection([
        ('ok', 'Within cycle'), ('due_soon', 'Due soon'), ('overdue', 'Overdue'),
        ('never', 'Never cleaned'),
    ], string='Cycle status', compute='_compute_days', store=True, index=True)
    last_lab = fields.Selection([
        ('pass', 'Pass'), ('fail', 'Fail'),
    ], string='Last lab result', compute='_compute_cycle', store=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [('code_facility_uniq', 'unique(code, facility_id)',
                         'That tank number is already used in this facility.')]

    @api.depends('code', 'position', 'capacity_gal')
    def _compute_name(self):
        pos = dict(self._fields['position'].selection)
        for t in self:
            t.name = '%s — %s%s' % (t.code or '', pos.get(t.position, ''),
                                    ' · %d gallons' % t.capacity_gal if t.capacity_gal else '')

    @api.depends('cleaning_ids.clean_date', 'cleaning_ids.state', 'cycle_months',
                 'cleaning_ids.lab_result')
    def _compute_cycle(self):
        for t in self:
            done = t.cleaning_ids.filtered(lambda c: c.state == 'done' and c.clean_date)
            last = done.sorted('clean_date', reverse=True)[:1]
            t.last_cleaned = last.clean_date if last else False
            t.last_lab = last.lab_result if last else False
            # 30-day months are close enough for a 6-month cycle and avoid a
            # dependency just to add months.
            t.next_due = (last.clean_date + timedelta(days=30 * (t.cycle_months or 6))
                          if last else False)

    @api.depends('next_due', 'last_cleaned')
    def _compute_days(self):
        today = fields.Date.context_today(self)
        for t in self:
            if not t.last_cleaned:
                t.days_left, t.status = 0, 'never'
                continue
            t.days_left = (t.next_due - today).days if t.next_due else 0
            t.status = ('overdue' if t.days_left < 0
                        else 'due_soon' if t.days_left <= 30 else 'ok')

    def action_start_cleaning(self):
        """Open a cleaning already carrying the standard step list, so the
        record cannot quietly omit the steps that make it a compliant clean."""
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'care.tank.cleaning',
                'view_mode': 'form',
                'context': {'default_tank_id': self.id,
                            'default_facility_id': self.facility_id.id}}

    @api.model
    def _cron_due(self):
        today = fields.Date.context_today(self)
        due = self.search(['|', ('status', '=', 'overdue'),
                           ('next_due', '<=', today + timedelta(days=30))])
        if not due or 'care.cafm.notification' not in self.env:
            return True
        staff = self.env['res.users'].sudo().search(
            [('groups_id', 'in', self.env.ref('base.group_erp_manager').id)], limit=8)
        for t in due:
            late = t.status == 'overdue'
            try:
                self.env['care.cafm.notification'].sudo().push(
                    staff,
                    _('🚰 Tank cleaning %s') % (_('Overdue') if late else _('Due soon')),
                    '%s — %s' % (t.name, t.facility_id.name or ''),
                    ntype='alert' if late else 'warning')
            except Exception:
                pass
        return True


class TankCleaning(models.Model):
    """One documented clean. The certificate and the lab result are the point."""
    _name = 'care.tank.cleaning'
    _description = 'Tank cleaning'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'clean_date desc, id desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    tank_id = fields.Many2one('care.tank.tank', string='Tank', required=True,
                              ondelete='cascade', index=True, tracking=True)
    facility_id = fields.Many2one(related='tank_id.facility_id', store=True, index=True)
    clean_date = fields.Date(string='Cleaning date', default=fields.Date.context_today,
                             required=True, tracking=True, index=True)
    crew_id = fields.Many2one('hr.employee', string='Done by', tracking=True)
    state = fields.Selection([
        ('draft', 'In progress'), ('done', 'Completed'), ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    # the steps that make it a compliant clean rather than a rinse
    step_drained = fields.Boolean(string='Drain the tank and isolate the feed line')
    step_sediment = fields.Boolean(string='Remove sediment')
    step_scrubbed = fields.Boolean(string='Clean walls and floor')
    step_disinfected = fields.Boolean(string='Disinfect with diluted chlorine')
    step_rinsed = fields.Boolean(string='Rinse until no chlorine trace remains')
    step_refilled = fields.Boolean(string='Refill')
    chlorine_ppm = fields.Float(string='Chlorine used (ppm)', default=50.0,
                                help='50 ppm for one hour of contact is the norm.')
    contact_minutes = fields.Integer(string='Contact time (minutes)', default=60)
    residual_ppm = fields.Float(string='Residual chlorine after rinsing (ppm)',
                                help='It must return to normal mains level before the tank goes back into service.')

    lab_sample_taken = fields.Boolean(string='Lab sample taken')
    lab_result = fields.Selection([
        ('pass', 'Meets the standard'), ('fail', 'Fail'),
    ], string='Lab result', tracking=True)
    lab_reference = fields.Char(string='Lab report number')
    certificate_no = fields.Char(string='Cleaning certificate number', copy=False, readonly=True,
                                 tracking=True)
    findings = fields.Text(string='Findings')
    completeness = fields.Integer(string='Steps completed %', compute='_compute_complete', store=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    STEPS = ['step_drained', 'step_sediment', 'step_scrubbed',
             'step_disinfected', 'step_rinsed', 'step_refilled']

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.tank.cleaning') or '/'
        return super().create(vals_list)

    @api.depends(*STEPS)
    def _compute_complete(self):
        for c in self:
            done = sum(1 for f in self.STEPS if c[f])
            c.completeness = int(100.0 * done / len(self.STEPS))

    def action_done(self):
        """A clean is only complete when every step is, because the certificate
        this issues is what a client shows an inspector."""
        for c in self:
            missing = [self._fields[f].string for f in self.STEPS if not c[f]]
            if missing:
                raise UserError(_('The certificate cannot be issued before every step is done.\nRemaining: %s')
                                % ', '.join(missing))
            if c.lab_sample_taken and not c.lab_result:
                raise UserError(_('A lab sample was recorded with no result — enter the result first.'))
            if c.lab_result == 'fail':
                raise UserError(_('The lab result failed — the tank must be cleaned again before approval.'))
            c.certificate_no = c.certificate_no or (
                self.env['ir.sequence'].next_by_code('care.tank.certificate') or c.name)
            c.state = 'done'
            c._notify_client()

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def _notify_client(self):
        self.ensure_one()
        if 'care.cafm.notification' not in self.env:
            return
        client = self.env['care.cafm.client'].sudo().search(
            [('partner_id', '=', self.facility_id.partner_id.id)], limit=1)
        if not client or not client.user_ids:
            return
        try:
            self.env['care.cafm.notification'].sudo().push(
                client.user_ids, _('🚰 Tank cleaned and certificate issued'),
                '%s — certificate %s' % (self.tank_id.name, self.certificate_no or ''),
                ntype='info')
        except Exception:
            pass
