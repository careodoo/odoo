# -*- coding: utf-8 -*-
from odoo import fields, models, api, _

class HRSocialContracts(models.Model):
    _name = 'hr.social.contracts'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name        = fields.Char(string='Name', track_visibility='onchange', required=True)
    contract_id = fields.Char(string='Contract Name', track_visibility='onchange', required=True)
    contract_no = fields.Char(string='Contract No', track_visibility='onchange', required=True)
    partner_id  = fields.Char(string='Contact', track_visibility='onchange', required=True)
    period      = fields.Integer(string='Period', track_visibility='onchange', required=True)
    contract_type  = fields.Selection([('family', 'Family Contract'), ('government', 'Government Contract')], string='Contract Type', track_visibility='onchange', required=True)
    bank_guarantee = fields.Float(string='Bank Guarantee')
    social_bank_guarantee = fields.Float(string='Social Bank Guarantee')
    capacity = fields.Integer(string='Capacity')
    finance_letter = fields.Char(string='Finance Letter')
    registered_labor = fields.Integer(string='Registered Labor', compute='compute_registered_labor')
    available_places = fields.Integer(string='Available Places', compute='compute_available_places')
    authorized_persons_line = fields.One2many('social.contracts.authorized.persons.line', 'social_contract_id', string='Authorized Persons Line')
    social_contracts_date_line = fields.One2many('social.contracts.date.line', 'social_contract_id', string='Dates Line')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)


    def compute_registered_labor(self):
        for record in self:
            employees = self.env['hr.employee'].search([('social_contract_id', '=', record.id)])
            record.registered_labor = len(employees)

    def compute_available_places(self):
        for record in self:
            record.available_places = record.capacity - record.registered_labor

class SocialContractsAuthorizedPersonsLine(models.Model):
    _name = 'social.contracts.authorized.persons.line'
    _order = 'id desc'

    name = fields.Many2one('social.contracts.authorized.persons', string='Employee Name', required=True)
    social_contract_id = fields.Many2one('hr.social.contracts', string='Contract Name')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)

class SocialContractsDateLine(models.Model):
    _name = 'social.contracts.date.line'
    _order = 'id desc'

    name = fields.Many2one('social.contracts.date.types', string='Date Type', required=True)
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    social_contract_id = fields.Many2one('hr.social.contracts', string='Contract Name')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)

class SocialContractsDateTypes(models.Model):
    _name = 'social.contracts.date.types'
    _order = 'id desc'

    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)