# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class CareCustody(models.Model):
    """Custody / handover register: items issued to a worker (ID, SIM, access
    card, tools, device, uniform...) with sign-out / return and condition.
    Outstanding custody blocks offboarding clearance."""
    _name = 'care.custody'
    _description = 'Custody / Handover'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'issue_date desc, id desc'

    name = fields.Char(string='Reference', default='/', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    item_type = fields.Selection([
        ('id_card', 'Company ID'),
        ('sim', 'SIM / Phone'),
        ('access_card', 'Access Card'),
        ('tools', 'Tools'),
        ('device', 'Device'),
        ('uniform', 'Uniform'),
        ('other', 'Other'),
    ], required=True, default='other', tracking=True)
    description = fields.Char(string='Item', required=True)
    issue_date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    return_date = fields.Date(tracking=True)
    value = fields.Monetary()
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    state = fields.Selection([
        ('issued', 'In Custody'),
        ('returned', 'Returned'),
        ('lost', 'Lost'),
        ('damaged', 'Damaged'),
    ], default='issued', required=True, tracking=True)
    note = fields.Text()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.custody') or '/'
        return super().create(vals_list)

    def action_return(self):
        self.write({'state': 'returned', 'return_date': fields.Date.today()})

    def action_lost(self):
        self.write({'state': 'lost'})

    def action_damaged(self):
        self.write({'state': 'damaged'})

    def action_reset(self):
        self.write({'state': 'issued', 'return_date': False})

    @api.model
    def outstanding_for_employee(self, employee_id):
        """Items still in custody (block offboarding until returned/settled)."""
        return self.search([('employee_id', '=', employee_id), ('state', '=', 'issued')])
