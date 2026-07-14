# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class CareAbscondingReport(models.Model):
    """Absence / absconding / sponsorship-transfer case (mockup 77).
    Legal-financial handling of unauthorized absence of sponsored labour:
    salary freeze, authority (PAM/MOI) reporting, financial impact and
    residency/file closure."""
    _name = 'care.absconding.report'
    _description = 'Absconding / Absence Case'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, id desc'

    name = fields.Char(string='Reference', default='/', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    report_type = fields.Selection([
        ('absence', 'Unauthorized Absence'),
        ('absconding', 'Absconding'),
        ('transfer', 'Sponsorship Transfer'),
        ('return', 'Return After Absence'),
    ], string='Type', default='absence', required=True, tracking=True)
    start_date = fields.Date(string='Absence Start', default=fields.Date.context_today, tracking=True)
    end_date = fields.Date(string='Resolved On', tracking=True)
    duration_days = fields.Integer(compute='_compute_duration', store=True)
    risk = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'),
    ], compute='_compute_risk', store=True, tracking=True)

    salary_frozen = fields.Boolean(tracking=True)
    authorities_notified = fields.Boolean(string='PAM/MOI Notified', tracking=True)
    financial_impact = fields.Monetary(string='Estimated Financial Impact', tracking=True)
    recruitment_cost_wasted = fields.Monetary(string='Wasted Recruitment Cost')
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)

    state = fields.Selection([
        ('detected', 'Absence Detected'),
        ('warned', 'Warned'),
        ('frozen', 'Salary Frozen'),
        ('reported', 'Reported to Authorities'),
        ('legal', 'Legal Action'),
        ('closed_return', 'Closed — Returned'),
        ('closed_final', 'Closed — Final'),
    ], default='detected', tracking=True)
    note = fields.Text()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('start_date', 'end_date', 'state')
    def _compute_duration(self):
        today = fields.Date.today()
        for rec in self:
            if not rec.start_date:
                rec.duration_days = 0
                continue
            end = rec.end_date if rec.state in ('closed_return', 'closed_final') and rec.end_date else today
            rec.duration_days = (end - rec.start_date).days

    @api.depends('report_type', 'duration_days')
    def _compute_risk(self):
        for rec in self:
            if rec.report_type == 'absconding':
                rec.risk = 'high'
            elif rec.report_type in ('transfer', 'return'):
                rec.risk = 'low'
            else:  # absence: escalates with duration
                d = rec.duration_days
                rec.risk = 'high' if d > 14 else ('medium' if d >= 7 else 'low')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.absconding.report') or '/'
        return super().create(vals_list)

    def action_warn(self):
        self.write({'state': 'warned'})

    def action_freeze_salary(self):
        self.write({'state': 'frozen', 'salary_frozen': True})

    def action_report_authorities(self):
        for rec in self:
            rec.write({
                'state': 'reported',
                'authorities_notified': True,
                'report_type': 'absconding',
            })
            if rec.employee_id:
                rec.employee_id.sudo().worker_status = 'absconding'

    def action_legal(self):
        self.write({'state': 'legal'})

    def action_return(self):
        for rec in self:
            rec.write({
                'state': 'closed_return',
                'report_type': 'return',
                'salary_frozen': False,
                'end_date': fields.Date.today(),
            })
            if rec.employee_id:
                rec.employee_id.sudo().worker_status = 'active'

    def action_close_final(self):
        self.write({'state': 'closed_final', 'end_date': fields.Date.today()})
