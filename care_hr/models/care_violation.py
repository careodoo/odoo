# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class CareTrafficViolation(models.Model):
    """Traffic violation. The fleet manager records it, assigns liability
    (driver vs company), and may request a salary deduction from HR. Approved
    driver-liable violations are deducted in payroll (CARE_VIOLATION).
    Does NOT touch the Fleet module (plate kept as text)."""
    _name = 'care.traffic.violation'
    _description = 'Traffic Violation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', default='/', copy=False, readonly=True)
    date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', tracking=True)
    plate = fields.Char(string='Vehicle Plate', tracking=True)
    driver_id = fields.Many2one('hr.employee', string='Driver', tracking=True)
    violation_type_id = fields.Many2one('care.violation.type', string='Violation', tracking=True)
    violation_type = fields.Char(string='Violation (legacy)', tracking=True)
    amount = fields.Monetary(required=True, tracking=True)
    notified = fields.Boolean(string='Driver Notified', readonly=True, copy=False)
    notified_date = fields.Datetime(readonly=True, copy=False)
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    responsible = fields.Selection([
        ('investigation', 'Under Investigation'),
        ('driver', 'Driver'),
        ('company', 'Company'),
    ], default='investigation', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Deduction Requested'),
        ('approved', 'Approved (HR)'),
        ('deducted', 'Deducted'),
        ('company_borne', 'Company Borne'),
        ('refused', 'Refused'),
    ], default='draft', tracking=True)
    payslip_id = fields.Many2one('hr.payslip', readonly=True, copy=False)
    approved_by = fields.Many2one('res.users', readonly=True, copy=False)
    note = fields.Text()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    legacy_id = fields.Integer(string='Legacy x_violation ID', index=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.traffic.violation') or '/'
        return super().create(vals_list)

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount < 0:
                raise ValidationError(_('Violation amount cannot be negative.'))

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
        if self.vehicle_id:
            self.plate = self.vehicle_id.license_plate or self.vehicle_id.name

    @api.onchange('violation_type_id')
    def _onchange_violation_type(self):
        if self.violation_type_id:
            self.amount = self.violation_type_id.amount
            self.violation_type = self.violation_type_id.name

    def action_notify_driver(self):
        """Notify the driver (appears in their Odoo mobile app inbox) that a
        traffic violation is registered against them."""
        for rec in self:
            if not rec.driver_id:
                raise UserError(_('Set the driver first.'))
            vname = rec.violation_type_id.name or rec.violation_type or _('Traffic violation')
            body = _('🚗 Traffic violation %s — %s · Amount: %s %s · Date: %s') % (
                rec.name, vname, rec.amount, rec.currency_id.symbol or '', rec.date)
            user = rec.driver_id.user_id
            if user:
                rec.message_post(body=body, partner_ids=[user.partner_id.id],
                                 subject=_('Traffic Violation Notice'))
                rec.activity_schedule(
                    'mail.mail_activity_data_todo', user_id=user.id,
                    summary=_('Traffic violation %s') % rec.name, note=body)
            else:
                rec.message_post(body=_('(No linked user) %s') % body)
            rec.write({'notified': True, 'notified_date': fields.Datetime.now()})
        return True

    @api.model
    def migrate_from_studio(self):
        """One-time, idempotent migration of legacy Studio x_violation data
        into care.traffic.violation (matched by legacy_id)."""
        Old = self.env.get('x_violation')
        if Old is None:
            return 0
        created = 0
        for old in Old.with_context(active_test=False).search([]):
            if self.search_count([('legacy_id', '=', old.id)]):
                continue
            veh = old.x_studio_many2one_field_MmTpF
            plate = (getattr(veh, 'license_plate', False) or getattr(veh, 'name', False)
                     or '') if veh else ''
            driver = old.x_studio_employee_driver
            vtype = old.x_studio_violation_type
            vtype_name = (vtype.x_name if vtype and 'x_name' in vtype._fields else
                          (vtype.display_name if vtype else '')) or ''
            d = old.x_studio_date or (old.x_studio_date_time.date()
                                      if old.x_studio_date_time else fields.Date.today())
            amount = old.x_studio_amount or 0.0
            paid = bool(old.x_studio_paid)
            if driver and amount > 0:
                state = 'deducted' if paid else 'approved'
                resp = 'driver'
            elif driver:
                state, resp = 'draft', 'driver'
            else:
                state, resp = 'company_borne', 'company'
            note = old.x_studio_notes or ''
            vals = {
                'name': old.x_name or '/',
                'date': d, 'plate': plate or False,
                'driver_id': driver.id if driver else False,
                'violation_type': vtype_name or False,
                'amount': amount, 'responsible': resp, 'state': state,
                'note': note, 'legacy_id': old.id,
            }
            rec = self.with_context(tracking_disable=True).create(vals)
            if paid and rec.state not in ('deducted',):
                rec.state = 'deducted'
            created += 1
        return created

    def action_request_deduction(self):
        for rec in self:
            if rec.responsible != 'driver' or not rec.driver_id:
                raise UserError(_('Set the responsible to "Driver" (with a driver) before requesting a deduction.'))
            rec.state = 'submitted'

    def action_approve(self):
        if not self.env.user.has_group('hr.group_hr_user'):
            raise UserError(_('Only HR can approve a violation deduction.'))
        self.write({'state': 'approved', 'approved_by': self.env.user.id})

    def action_company_borne(self):
        self.write({'state': 'company_borne', 'responsible': 'company'})

    def action_refuse(self):
        self.write({'state': 'refused'})

    def action_reset(self):
        self.write({'state': 'draft', 'approved_by': False})
