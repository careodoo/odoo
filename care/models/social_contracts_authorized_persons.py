# -*- coding: utf-8 -*-
from odoo import fields, models, api, _

class SocialContractsAuthorizedPersons(models.Model):
    _name = 'social.contracts.authorized.persons'
    _inherit = ['mail.thread']
    _rec_name = 'employee_id'
    _order = 'id desc'

    employee_id = fields.Many2one('hr.employee', string='Employee Name', required=True)
    name = fields.Char(string='Name')
    parent_id = fields.Many2one('hr.employee', string='Manager Name')
    department_id = fields.Many2one('hr.department', string='Department Name')
    pin = fields.Char(string='Pin Code')
    identification_id = fields.Char(string='Identification ID')
    country_id = fields.Many2one('res.country', string='Nationality (Country)')
    contract_ids = fields.Many2many('hr.social.contracts', compute='compute_contracts', string='Contracts')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)
    active = fields.Boolean(default=True)

    def compute_contracts(self):
        for record in self:
            record.contract_ids = False
            contracts = self.env['social.contracts.authorized.persons.line'].search([('name', '=', record.id)])
            for contract in contracts:
                record.contract_ids += contract.social_contract_id


    @api.onchange('employee_id')
    def set_employee_info(self):
        if self.employee_id:
            self.name = self.employee_id.name
            self.parent_id = self.employee_id.parent_id.id
            self.department_id = self.employee_id.department_id.id
            self.pin = self.employee_id.pin
            self.identification_id = self.employee_id.identification_id
            self.country_id = self.employee_id.country_id.id