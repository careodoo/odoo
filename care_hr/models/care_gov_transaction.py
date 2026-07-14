# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import fields, models, api, _


class CareGovTransaction(models.Model):
    """Government transaction tracker (PRO / مندوب): each residency/permit/
    civil-id/authentication transaction with assignee, fees, deadline and SLA."""
    _name = 'care.gov.transaction'
    _description = 'Government Transaction (PRO)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'deadline, id desc'

    name = fields.Char(string='Reference', default='/', copy=False, readonly=True)
    transaction_type = fields.Selection([
        ('residency_new', 'New Residency'),
        ('residency_renew', 'Renew Residency'),
        ('work_permit', 'Work Permit'),
        ('civil_id', 'Civil ID (PACI)'),
        ('contract_auth', 'Contract Authentication'),
        ('transfer', 'Sponsorship Transfer'),
        ('other', 'Other'),
    ], required=True, default='residency_renew', tracking=True)
    employee_id = fields.Many2one('hr.employee', tracking=True)
    manpower_file_id = fields.Many2one('care.manpower.file', string='Manpower File', tracking=True)
    pro_id = fields.Many2one('res.users', string='PRO / Mandoob', tracking=True)
    fees = fields.Monetary()
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    submit_date = fields.Date(default=fields.Date.context_today, tracking=True)
    deadline = fields.Date(tracking=True)
    overdue = fields.Boolean(compute='_compute_overdue', search='_search_overdue')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('in_progress', 'In Progress'),
        ('waiting', 'Waiting Document'),
        ('done', 'Completed'),
        ('rejected', 'Rejected'),
    ], default='draft', tracking=True)
    note = fields.Text()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('deadline', 'state')
    def _compute_overdue(self):
        today = fields.Date.today()
        for rec in self:
            rec.overdue = bool(rec.deadline and rec.deadline < today
                               and rec.state not in ('done', 'rejected'))

    def _search_overdue(self, operator, value):
        today = fields.Date.today()
        ids = self.search([('deadline', '<', today),
                           ('state', 'not in', ('done', 'rejected'))]).ids
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [('id', 'in', ids)]
        return [('id', 'not in', ids)]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.gov.transaction') or '/'
        return super().create(vals_list)

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_progress(self):
        self.write({'state': 'in_progress'})

    def action_waiting(self):
        self.write({'state': 'waiting'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    @api.model
    def action_generate_due_renewals(self, days=30):
        """One-click (mockup 40): create draft residency-renewal transactions
        for every employee whose residency expires within `days` and who has
        no open renewal transaction yet. Returns an action listing the result."""
        today = fields.Date.today()
        limit_date = today + timedelta(days=days)
        due = self.env['hr.employee'].search([
            ('residency_end_date', '!=', False),
            ('residency_end_date', '>=', today),
            ('residency_end_date', '<=', limit_date),
        ])
        created = self.browse()
        for emp in due:
            open_tx = self.search_count([
                ('employee_id', '=', emp.id),
                ('transaction_type', '=', 'residency_renew'),
                ('state', 'not in', ('done', 'rejected')),
            ])
            if open_tx:
                continue
            created |= self.create({
                'transaction_type': 'residency_renew',
                'employee_id': emp.id,
                'deadline': emp.residency_end_date,
            })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generated Renewals (%s)') % len(created),
            'res_model': 'care.gov.transaction',
            'view_mode': 'tree,kanban,form',
            'domain': [('id', 'in', created.ids)],
            'context': {'search_default_open': 1},
        }
