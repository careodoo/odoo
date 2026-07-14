# -*- coding: utf-8 -*-
import base64
from datetime import timedelta
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class CarePassport(models.Model):
    """Employee passport kept in the travel archive (for residency etc.).
    Each passport carries a barcode sticker; movements (out/in) are tracked."""
    _name = 'care.passport'
    _description = 'Employee Passport (Archive)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'expiry_date'

    name = fields.Char(string='Barcode / Ref', default='New', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    employee_english_name = fields.Char(related='employee_id.english_name', string='Employee (EN)')
    # Unified passport data: shared (two-way) with the employee record so the
    # passport number/dates/nationality are identical across all modules.
    passport_no = fields.Char(string='Passport No.', related='employee_id.passport_no',
                              store=True, readonly=False, tracking=True)
    country_id = fields.Many2one('res.country', string='Nationality',
                                 related='employee_id.country_id', store=True, readonly=False)
    issue_date = fields.Date(string='Issue Date', related='employee_id.release_date',
                             store=True, readonly=False, tracking=True)
    expiry_date = fields.Date(string='Expiry Date', related='employee_id.end_date',
                              store=True, readonly=False, tracking=True)
    days_to_expiry = fields.Integer(compute='_compute_expiry', store=True)
    expiry_state = fields.Selection([
        ('valid', 'Valid'), ('expiring', 'Expiring'), ('expired', 'Expired'),
    ], compute='_compute_expiry', store=True)
    state = fields.Selection([
        ('in_archive', 'In Archive'), ('out', 'Out'),
    ], default='in_archive', required=True, tracking=True)
    shelf_location = fields.Char(string='Shelf / Location', tracking=True)
    out_reason = fields.Selection([
        ('travel_leave', 'Travel - Leave'),
        ('final_exit', 'Final Exit'),
        ('pro_residency', 'PRO - Residency'),
    ], tracking=True)
    holder_id = fields.Many2one('hr.employee', string='Current Holder', tracking=True)
    expected_return = fields.Date(tracking=True)
    last_movement_id = fields.Many2one('care.passport.movement', readonly=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    barcode_src = fields.Char(compute='_compute_barcode_src')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Passport barcode/ref must be unique.'),
    ]

    @api.depends('expiry_date')
    def _compute_expiry(self):
        today = fields.Date.today()
        for rec in self:
            if rec.expiry_date:
                rec.days_to_expiry = (rec.expiry_date - today).days
                if rec.days_to_expiry < 0:
                    rec.expiry_state = 'expired'
                elif rec.days_to_expiry <= 90:
                    rec.expiry_state = 'expiring'
                else:
                    rec.expiry_state = 'valid'
            else:
                rec.days_to_expiry = 0
                rec.expiry_state = 'valid'

    def _compute_barcode_src(self):
        IR = self.env['ir.actions.report']
        for rec in self:
            try:
                bc = IR.barcode('Code128', rec.name or 'NEW', width=480, height=90, humanreadable=1)
                rec.barcode_src = 'data:image/png;base64,' + base64.b64encode(bc).decode()
            except Exception:
                rec.barcode_src = False

    @api.onchange('employee_id')
    def _onchange_employee(self):
        if self.employee_id and not self.country_id:
            self.country_id = self.employee_id.country_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.passport') or 'New'
        return super().create(vals_list)

    @api.model
    def _cron_expiry_reminder(self):
        """Schedule a renewal activity for passports expiring within 30 days."""
        today = fields.Date.today()
        soon = today + timedelta(days=30)
        recs = self.search([('expiry_date', '!=', False), ('expiry_date', '<=', soon),
                            ('expiry_date', '>=', today)])
        for rec in recs:
            if not rec.activity_ids.filtered(lambda a: a.summary == 'Passport renewal due'):
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('Passport renewal due'),
                    note=_('Passport %s of %s expires on %s') % (
                        rec.passport_no or rec.name, rec.employee_id.name, rec.expiry_date))


class CarePassportMovement(models.Model):
    """Bulk passport check-out / check-in via barcode scanning."""
    _name = 'care.passport.movement'
    _description = 'Passport Movement (bulk)'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char(default='New', copy=False, readonly=True)
    movement_type = fields.Selection([
        ('out', 'Check-Out'), ('in', 'Check-In / Return'),
    ], default='out', required=True, tracking=True)
    reason = fields.Selection([
        ('travel_leave', 'Travel - Leave'),
        ('final_exit', 'Final Exit'),
        ('pro_residency', 'PRO - Residency'),
        ('return', 'Return to Archive'),
    ], tracking=True)
    custodian_id = fields.Many2one('hr.employee', string='Custodian (PRO / Employee)', tracking=True)
    date = fields.Datetime(default=fields.Datetime.now, tracking=True)
    expected_return = fields.Date()
    authority = fields.Char(string='Purpose / Authority')
    shelf_location = fields.Char(string='Return Shelf')
    passport_ids = fields.Many2many('care.passport', string='Passports')
    passport_count = fields.Integer(compute='_compute_count')
    scan_barcode = fields.Char(string='Scan Barcode', store=False)
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], default='draft', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    barcode_src = fields.Char(compute='_compute_codes')
    qr_src = fields.Char(compute='_compute_codes')

    @api.depends('passport_ids')
    def _compute_count(self):
        for rec in self:
            rec.passport_count = len(rec.passport_ids)

    def _compute_codes(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
        IR = self.env['ir.actions.report']
        for rec in self:
            try:
                bc = IR.barcode('Code128', rec.name or 'NEW', width=520, height=90, humanreadable=1)
                rec.barcode_src = 'data:image/png;base64,' + base64.b64encode(bc).decode()
                url = "%s/web#id=%s&model=care.passport.movement&view_type=form" % (base, rec.id)
                qr = IR.barcode('QR', url, width=140, height=140)
                rec.qr_src = 'data:image/png;base64,' + base64.b64encode(qr).decode()
            except Exception:
                rec.barcode_src = rec.qr_src = False

    @api.onchange('scan_barcode')
    def _onchange_scan(self):
        code = (self.scan_barcode or '').strip()
        if not code:
            return
        pp = self.env['care.passport'].search([('name', '=', code)], limit=1) or \
            self.env['care.passport'].search([('passport_no', '=', code)], limit=1)
        if pp:
            if pp not in self.passport_ids:
                self.passport_ids = [(4, pp.id)]
        else:
            return {'warning': {'title': _('Not found'),
                                'message': _('No passport with barcode %s') % code}}
        self.scan_barcode = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.passport.movement') or 'New'
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            if not rec.passport_ids:
                raise UserError(_('Scan at least one passport.'))
            for pp in rec.passport_ids:
                if rec.movement_type == 'out':
                    pp.write({
                        'state': 'out', 'out_reason': rec.reason,
                        'holder_id': rec.custodian_id.id, 'expected_return': rec.expected_return,
                        'last_movement_id': rec.id,
                    })
                else:
                    pp.write({
                        'state': 'in_archive', 'out_reason': False, 'holder_id': False,
                        'expected_return': False, 'last_movement_id': rec.id,
                        'shelf_location': rec.shelf_location or pp.shelf_location,
                    })
            rec.state = 'done'
        return True

    def action_reset(self):
        self.write({'state': 'draft'})
