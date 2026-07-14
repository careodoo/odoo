# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class CareDeployment(models.Model):
    """Worker deployment to a project / site."""
    _name = 'care.deployment'
    _description = 'Worker Deployment'
    _inherit = ['mail.thread']
    _order = 'start_date desc, id desc'

    name = fields.Char(default='New', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    project_id = fields.Many2one('project.project', string='Project', tracking=True)
    site_location = fields.Char(string='Site / Location', tracking=True)
    start_date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    end_date = fields.Date(tracking=True)
    state = fields.Selection([('active', 'Active'), ('ended', 'Ended')],
                             default='active', required=True, tracking=True)
    note = fields.Text()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.deployment') or 'New'
        return super().create(vals_list)

    def action_end(self):
        self.write({'state': 'ended', 'end_date': fields.Date.today()})


class CareWorkerQuality(models.Model):
    """Worker quality rating → classification tier."""
    _name = 'care.worker.quality'
    _description = 'Worker Quality Rating'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char(default='New', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    attendance_score = fields.Integer(string='Attendance', default=0)
    discipline_score = fields.Integer(string='Discipline', default=0)
    skill_score = fields.Integer(string='Skill', default=0)
    appearance_score = fields.Integer(string='Appearance', default=0)
    overall = fields.Float(compute='_compute_overall', store=True)
    tier = fields.Selection([
        ('a', 'A — Excellent'), ('b', 'B — Good'),
        ('c', 'C — Average'), ('d', 'D — Below'),
    ], compute='_compute_overall', store=True)
    evaluator_id = fields.Many2one('res.users', default=lambda s: s.env.user)
    notes = fields.Text()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('attendance_score', 'discipline_score', 'skill_score', 'appearance_score')
    def _compute_overall(self):
        for rec in self:
            o = (rec.attendance_score + rec.discipline_score + rec.skill_score
                 + rec.appearance_score) / 4.0
            rec.overall = round(o, 1)
            rec.tier = ('a' if o >= 85 else 'b' if o >= 70 else 'c' if o >= 50 else 'd')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.worker.quality') or 'New'
        return super().create(vals_list)


class CareRequest(models.Model):
    """Unified administrative requests hub."""
    _name = 'care.request'
    _description = 'Administrative Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default='New', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    request_type = fields.Selection([
        ('leave', 'Leave'), ('advance', 'Advance / Loan'), ('document', 'Document / Letter'),
        ('transfer', 'Transfer'), ('complaint', 'Complaint'), ('other', 'Other'),
    ], default='other', required=True, tracking=True)
    subject = fields.Char(required=True)
    description = fields.Text()
    date = fields.Date(default=fields.Date.context_today, required=True)
    handler_id = fields.Many2one('res.users', string='Handler')
    state = fields.Selection([
        ('submitted', 'Submitted'), ('in_progress', 'In Progress'),
        ('approved', 'Approved'), ('rejected', 'Rejected'), ('done', 'Done'),
    ], default='submitted', tracking=True)
    response = fields.Text()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.request') or 'New'
        return super().create(vals_list)

    def action_progress(self):
        self.write({'state': 'in_progress'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_done(self):
        self.write({'state': 'done'})
