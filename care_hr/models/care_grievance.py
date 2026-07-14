# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import fields, models, api, _


class CareGrievance(models.Model):
    """Worker grievance / complaint with an SLA, investigation and resolution."""
    _name = 'care.grievance'
    _description = 'Grievance / Complaint'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', default='/', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    category = fields.Selection([
        ('wages', 'Wages / Allowances'),
        ('housing', 'Housing'),
        ('treatment', 'Supervisor / Treatment'),
        ('safety', 'Safety'),
        ('other', 'Other'),
    ], required=True, default='other', tracking=True)
    channel = fields.Selection([
        ('mobile', 'Mobile App'),
        ('phone', 'Phone'),
        ('in_person', 'In Person'),
        ('kiosk', 'Kiosk'),
    ], default='in_person', tracking=True)
    description = fields.Text(required=True)
    date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    sla_days = fields.Integer(string='SLA (days)', default=3)
    deadline = fields.Date(compute='_compute_deadline', store=True)
    overdue = fields.Boolean(compute='_compute_overdue', search='_search_overdue')
    assigned_to = fields.Many2one('res.users', string='Handler', tracking=True)
    state = fields.Selection([
        ('submitted', 'Submitted'),
        ('triage', 'Triage'),
        ('investigation', 'Investigation'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('refused', 'Refused'),
    ], default='submitted', tracking=True)
    resolution = fields.Text(tracking=True)
    satisfaction = fields.Selection([
        ('satisfied', 'Satisfied'),
        ('neutral', 'Neutral'),
        ('unsatisfied', 'Unsatisfied'),
    ], tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('date', 'sla_days')
    def _compute_deadline(self):
        for rec in self:
            rec.deadline = (rec.date + timedelta(days=rec.sla_days)) if rec.date else False

    @api.depends('deadline', 'state')
    def _compute_overdue(self):
        today = fields.Date.today()
        for rec in self:
            rec.overdue = bool(rec.deadline and rec.deadline < today
                               and rec.state not in ('resolved', 'closed', 'refused'))

    def _search_overdue(self, operator, value):
        today = fields.Date.today()
        ids = self.search([('deadline', '<', today),
                           ('state', 'not in', ('resolved', 'closed', 'refused'))]).ids
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [('id', 'in', ids)]
        return [('id', 'not in', ids)]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.grievance') or '/'
        return super().create(vals_list)

    def action_triage(self):
        self.write({'state': 'triage'})

    def action_investigate(self):
        self.write({'state': 'investigation'})

    def action_resolve(self):
        self.write({'state': 'resolved'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_refuse(self):
        self.write({'state': 'refused'})
