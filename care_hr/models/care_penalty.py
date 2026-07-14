# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class CarePenaltyType(models.Model):
    """Per-project penalty catalogue. Each project defines its own penalty
    types (violation + amount + required approval level)."""
    _name = 'care.penalty.type'
    _description = 'Penalty Type (per project)'
    _order = 'project_id, name'

    name = fields.Char(string='Violation', required=True, translate=True)
    project_id = fields.Many2one('project.project', string='Project', ondelete='cascade')
    amount = fields.Monetary(string='Default Amount', required=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    approval_level = fields.Selection([
        ('supervisor', 'Supervisor'),
        ('hr', 'Supervisor + HR'),
    ], string='Approval Required', default='supervisor')
    active = fields.Boolean(default=True)
    note = fields.Char(string='Notes')


class CarePenalty(models.Model):
    """A penalty imposed on a worker (NOT the value of an absent hour/day).
    Defined from the project catalogue, applied per worker, approved, then
    reflected as a payroll deduction line (CARE_PENALTY)."""
    _name = 'care.penalty'
    _description = 'Worker Penalty'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', default='/', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    project_id = fields.Many2one('project.project', string='Project', tracking=True)
    penalty_type_id = fields.Many2one(
        'care.penalty.type', string='Violation',
        domain="['|', ('project_id','=',project_id), ('project_id','=',False)]")
    amount = fields.Monetary(required=True, tracking=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    reason = fields.Text(tracking=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Evidence')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('done', 'Deducted'),
        ('refused', 'Refused'),
    ], default='draft', tracking=True)
    approved_by = fields.Many2one('res.users', readonly=True, copy=False)
    payslip_id = fields.Many2one('hr.payslip', readonly=True, copy=False)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.onchange('penalty_type_id')
    def _onchange_penalty_type(self):
        if self.penalty_type_id:
            self.amount = self.penalty_type_id.amount

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.penalty') or '/'
        return super().create(vals_list)

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_('Penalty amount must be positive.'))

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        self.write({'state': 'approved', 'approved_by': self.env.user.id})

    def action_refuse(self):
        self.write({'state': 'refused'})

    def action_reset(self):
        self.write({'state': 'draft', 'approved_by': False})
