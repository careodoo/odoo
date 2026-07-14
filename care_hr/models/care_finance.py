# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class CareBonus(models.Model):
    """Employee bonus — approved then paid inside the payslip (CARE_BONUS) or cash."""
    _name = 'care.bonus'
    _description = 'Employee Bonus'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    bonus_type = fields.Selection([
        ('performance', 'Performance'), ('eid', 'Eid / Festival'),
        ('annual', 'Annual'), ('other', 'Other'),
    ], default='performance', required=True, tracking=True)
    amount = fields.Monetary(required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    payment_method = fields.Selection([
        ('in_payslip', 'Inside Payslip'), ('cash', 'Cash')],
        default='in_payslip', required=True, tracking=True)
    reason = fields.Text()
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'),
        ('done', 'Processed'), ('refused', 'Refused')], default='draft', tracking=True)
    approved_by = fields.Many2one('res.users', readonly=True, copy=False)
    payslip_id = fields.Many2one('hr.payslip', readonly=True, copy=False)
    cash_paid = fields.Boolean(copy=False)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.bonus') or '/'
        return super().create(vals_list)

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_('Bonus amount must be positive.'))

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        if not self.env.user.has_group('hr.group_hr_user'):
            raise UserError(_('Only HR can approve a bonus.'))
        self.write({'state': 'approved', 'approved_by': self.env.user.id})

    def action_refuse(self):
        self.write({'state': 'refused'})

    def action_mark_cash_paid(self):
        for rec in self:
            if rec.payment_method != 'cash' or rec.state != 'approved':
                raise UserError(_('Only approved cash bonuses can be marked paid.'))
            rec.write({'cash_paid': True, 'state': 'done'})


class CareEosLiability(models.Model):
    """End-of-service provision per employee (termination basis) — the company's
    accrued EOS liability. Refreshed by a scan."""
    _name = 'care.eos.liability'
    _description = 'EOS Liability (provision)'
    _order = 'provision_amount desc'

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade')
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    join_date = fields.Date()
    last_day = fields.Date(string='As Of')
    service_years = fields.Float()
    basic_wage = fields.Monetary()
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    provision_days = fields.Float(string='Indemnity Days')
    provision_amount = fields.Monetary(string='EOS Provision')
    scan_date = fields.Date(default=fields.Date.context_today)

    @api.model
    def run_scan(self):
        """Rebuild the EOS provision per active employee (termination basis)."""
        ICP = self.env['ir.config_parameter'].sudo()
        f5 = int(ICP.get_param('care_hr.eos_first5_days') or 15)
        a5 = int(ICP.get_param('care_hr.eos_after5_days') or 30)
        cap_years = float(ICP.get_param('care_hr.eos_cap_years') or 1.5)
        today = fields.Date.today()
        self.search([]).unlink()
        Emp = self.env['hr.employee']
        emps = Emp.search([('active', '=', True), ('contract_id', '!=', False)])
        vals = []
        for e in emps:
            join = e.first_contract_date or e.joining_date
            wage = e.contract_id.wage if e.contract_id else 0.0
            if not join or not wage or join >= today:
                continue
            years = (today - join).days / 365.25
            daily = wage / 26.0
            days = years * f5 if years <= 5 else 5 * f5 + (years - 5) * a5
            gross = days * daily
            cap = cap_years * 12 * wage
            if cap and gross > cap:
                gross = cap
            vals.append({
                'employee_id': e.id, 'join_date': join, 'last_day': today,
                'service_years': round(years, 2), 'basic_wage': wage,
                'provision_days': round(days, 1), 'provision_amount': round(gross, 3),
            })
        if vals:
            self.create(vals)
        return len(vals)

    def action_run_scan(self):
        n = self.run_scan()
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('EOS Liability'), 'message': _('%s employees scanned.') % n,
                           'type': 'success', 'next': {'type': 'ir.actions.act_window',
                           'res_model': 'care.eos.liability', 'view_mode': 'tree,form,pivot'}}}
