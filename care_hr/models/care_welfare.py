# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class CareExpenseClaim(models.Model):
    """Employee expense reimbursement / petty-cash claim."""
    _name = 'care.expense.claim'
    _description = 'Expense Claim'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'expense_date desc, id desc'

    name = fields.Char(default='New', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    expense_type = fields.Selection([
        ('transport', 'Transport / Mission'), ('tools', 'Tools / Equipment'),
        ('fees', 'Fees'), ('medical', 'Medical'), ('supplies', 'Supplies'),
        ('other', 'Other'),
    ], default='transport', required=True, tracking=True)
    expense_date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    amount = fields.Monetary(required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    receipt = fields.Binary(string='Receipt', attachment=True)
    receipt_filename = fields.Char()
    has_receipt = fields.Boolean(compute='_compute_has_receipt', store=True)
    description = fields.Char(string='Description')
    reimburse_method = fields.Selection([
        ('in_payslip', 'Via Payslip'), ('cash', 'Cash')], default='cash', tracking=True)
    custody_id = fields.Many2one('care.custody', string='Cash Custody',
                                 help="Cash custody this claim is settled against.")
    approved_by = fields.Many2one('res.users', readonly=True, copy=False)
    reimbursed_date = fields.Date(readonly=True, copy=False)
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'),
        ('mgr_approved', 'Manager Approved'), ('approved', 'Finance Approved'),
        ('reimbursed', 'Reimbursed'), ('refused', 'Refused'),
    ], default='draft', required=True, tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('receipt')
    def _compute_has_receipt(self):
        for r in self:
            r.has_receipt = bool(r.receipt)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.expense.claim') or 'New'
        return super().create(vals_list)

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_mgr_approve(self):
        self.write({'state': 'mgr_approved'})

    def action_finance_approve(self):
        self.write({'state': 'approved', 'approved_by': self.env.user.id})

    def action_reimburse(self):
        for r in self:
            if r.state != 'approved':
                raise UserError(_("Only finance-approved claims can be reimbursed."))
        self.write({'state': 'reimbursed', 'reimbursed_date': fields.Date.today()})

    def action_refuse(self):
        self.write({'state': 'refused'})

    def action_reset(self):
        self.write({'state': 'draft'})


class CareInsurancePolicy(models.Model):
    """Health / life insurance policy per employee (Kuwait mandatory health)."""
    _name = 'care.insurance.policy'
    _description = 'Insurance Policy'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'expiry_date'

    name = fields.Char(default='New', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    insurer = fields.Char(string='Insurer', tracking=True)
    policy_no = fields.Char(string='Policy No.', tracking=True)
    insurance_type = fields.Selection([
        ('health', 'Health'), ('life', 'Life'), ('accident', 'Accident'), ('other', 'Other'),
    ], default='health', required=True, tracking=True)
    category = fields.Char(string='Category', help="Coverage tier, e.g. A/B/C.")
    start_date = fields.Date(tracking=True)
    expiry_date = fields.Date(required=True, tracking=True)
    premium = fields.Monetary()
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    days_to_expiry = fields.Integer(compute='_compute_state', store=True)
    state = fields.Selection([
        ('valid', 'Valid'), ('renew_soon', 'Renew Soon'), ('expired', 'Expired'),
    ], compute='_compute_state', store=True)
    note = fields.Text()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.insurance.policy') or 'New'
        return super().create(vals_list)

    @api.depends('expiry_date')
    def _compute_state(self):
        today = fields.Date.context_today(self)
        for r in self:
            if not r.expiry_date:
                r.days_to_expiry = 0
                r.state = 'valid'
                continue
            d = (r.expiry_date - today).days
            r.days_to_expiry = d
            r.state = 'expired' if d < 0 else ('renew_soon' if d <= 60 else 'valid')

    @api.model
    def _cron_insurance_reminder(self):
        """Schedule a renewal activity for policies expiring within 60 days."""
        soon = fields.Date.context_today(self) + relativedelta(days=60)
        for p in self.search([('expiry_date', '<=', soon), ('expiry_date', '!=', False)]):
            if not p.activity_ids:
                p.activity_schedule(
                    'mail.mail_activity_data_todo',
                    date_deadline=p.expiry_date,
                    summary=_('Insurance %s expiring %s') % (p.policy_no or p.name, p.expiry_date))
        return True


class CareGosi(models.Model):
    """GOSI (social insurance) registration + monthly contribution per employee.
    The employee share is deducted in payroll via the CARE_GOSI rule."""
    _name = 'care.gosi'
    _description = 'GOSI Registration'
    _inherit = ['mail.thread']
    _order = 'employee_id'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    registration_no = fields.Char(string='GOSI No.', tracking=True)
    gosi_wage = fields.Monetary(string='Contributory Wage', tracking=True,
                                help="Wage the contribution is calculated on (defaults to contract wage).")
    company_rate = fields.Float(string='Company %', default=11.5, tracking=True)
    employee_rate = fields.Float(string='Employee %', default=8.0, tracking=True)
    company_amount = fields.Monetary(compute='_compute_amounts', store=True)
    employee_amount = fields.Monetary(compute='_compute_amounts', store=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    _sql_constraints = [('emp_uniq', 'unique(employee_id)', 'One GOSI record per employee.')]

    @api.onchange('employee_id')
    def _onchange_employee(self):
        if self.employee_id and self.employee_id.contract_id and not self.gosi_wage:
            self.gosi_wage = self.employee_id.contract_id.wage

    @api.depends('gosi_wage', 'company_rate', 'employee_rate')
    def _compute_amounts(self):
        for r in self:
            r.company_amount = round((r.gosi_wage or 0.0) * (r.company_rate or 0.0) / 100.0, 3)
            r.employee_amount = round((r.gosi_wage or 0.0) * (r.employee_rate or 0.0) / 100.0, 3)
