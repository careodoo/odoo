# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import fields, models, api, _


class CareSitePermit(models.Model):
    """Site access / security permit for government or sensitive sites.
    A worker may not be deployed to a secured site without a valid permit."""
    _name = 'care.site.permit'
    _description = 'Site / Security Permit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'expiry_date, id desc'

    name = fields.Char(string='Reference', default='/', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    site_name = fields.Char(string='Site / Authority', tracking=True)
    permit_type = fields.Char(string='Permit Type', tracking=True)
    security_clearance = fields.Selection([
        ('pending', 'Pending'),
        ('passed', 'Passed'),
        ('rejected', 'Rejected'),
    ], default='pending', tracking=True)
    issue_date = fields.Date(tracking=True)
    expiry_date = fields.Date(tracking=True)
    days_to_expiry = fields.Integer(compute='_compute_expiry')
    is_valid = fields.Boolean(compute='_compute_expiry', search='_search_is_valid')
    state = fields.Selection([
        ('draft', 'Requested'),
        ('screening', 'Security Screening'),
        ('issued', 'Issued'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked'),
    ], default='draft', tracking=True)
    note = fields.Text()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('expiry_date', 'state', 'security_clearance')
    def _compute_expiry(self):
        today = fields.Date.today()
        for rec in self:
            rec.days_to_expiry = (rec.expiry_date - today).days if rec.expiry_date else 0
            rec.is_valid = bool(
                rec.state == 'issued' and rec.security_clearance == 'passed'
                and (not rec.expiry_date or rec.expiry_date >= today))

    def _search_is_valid(self, operator, value):
        today = fields.Date.today()
        ids = self.search([('state', '=', 'issued'),
                           ('security_clearance', '=', 'passed'),
                           '|', ('expiry_date', '=', False),
                           ('expiry_date', '>=', today)]).ids
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [('id', 'in', ids)]
        return [('id', 'not in', ids)]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.site.permit') or '/'
        return super().create(vals_list)

    def action_screening(self):
        self.write({'state': 'screening'})

    def action_issue(self):
        self.write({'state': 'issued', 'security_clearance': 'passed'})

    def action_revoke(self):
        self.write({'state': 'revoked'})

    def action_reject(self):
        self.write({'state': 'draft', 'security_clearance': 'rejected'})

    @api.model
    def _cron_expire(self):
        today = fields.Date.today()
        self.search([('state', '=', 'issued'), ('expiry_date', '<', today)]).write({'state': 'expired'})
