# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class CareLoan(models.Model):
    """Employee loan / salary advance with automatic monthly installment
    deduction on the payslip (native, no external dependency)."""
    _name = 'care.loan'
    _description = 'Loan / Advance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default='New', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    loan_type = fields.Selection([
        ('advance', 'Salary Advance'), ('loan', 'Loan'),
    ], default='advance', required=True, tracking=True)
    date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    amount = fields.Monetary(string='Amount', required=True, tracking=True)
    installments = fields.Integer(string='Installments', default=1, required=True, tracking=True,
                                  help="Number of monthly deductions.")
    installment_amount = fields.Monetary(string='Monthly Installment',
                                         compute='_compute_amounts', store=True)
    start_date = fields.Date(string='First Deduction', default=lambda s: fields.Date.context_today(s),
                             tracking=True)
    paid_amount = fields.Monetary(string='Paid', readonly=True, copy=False)
    balance = fields.Monetary(string='Balance', compute='_compute_amounts', store=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    reason = fields.Char()
    approved_by = fields.Many2one('res.users', readonly=True, copy=False)
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'),
        ('ongoing', 'Deducting'), ('paid', 'Fully Paid'), ('refused', 'Refused'),
    ], default='draft', required=True, tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('amount', 'installments', 'paid_amount')
    def _compute_amounts(self):
        for r in self:
            r.installment_amount = round(r.amount / r.installments, 3) if r.installments else r.amount
            r.balance = (r.amount or 0.0) - (r.paid_amount or 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.loan') or 'New'
        return super().create(vals_list)

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        for r in self:
            if r.amount <= 0 or r.installments <= 0:
                raise UserError(_("Set a positive amount and installment count."))
        self.write({'state': 'approved', 'approved_by': self.env.user.id})

    def action_start(self):
        self.write({'state': 'ongoing'})

    def action_refuse(self):
        self.write({'state': 'refused'})

    def action_reset(self):
        self.write({'state': 'draft'})

    def _register_installment(self, amount):
        """Called from payroll when an installment is actually deducted."""
        self.ensure_one()
        paid = (self.paid_amount or 0.0) + amount
        vals = {'paid_amount': paid}
        if paid >= self.amount:
            vals['state'] = 'paid'
        elif self.state == 'approved':
            vals['state'] = 'ongoing'
        self.write(vals)

    @api.model
    def _due_installment(self, employee_id, date_from, date_to):
        """Total installment due for an employee in the slip period."""
        loans = self.search([
            ('employee_id', '=', employee_id),
            ('state', 'in', ('approved', 'ongoing')),
            ('start_date', '<=', date_to),
        ])
        total = 0.0
        due = self.browse()
        for ln in loans:
            if ln.balance <= 0:
                continue
            inst = min(ln.installment_amount, ln.balance)
            total += inst
            due |= ln
        return total, due
