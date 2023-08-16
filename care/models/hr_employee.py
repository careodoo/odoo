# -*- coding: utf-8 -*-
from odoo import fields, models, api, _

class HREmployee(models.Model):
    _inherit = 'hr.employee'

    english_name = fields.Char(string="English Name")
    civil_code = fields.Char(string="Civil Code")
    moi_number = fields.Char(string="MOI Number")
    enter_date = fields.Date(string="Enter Date")
    residency_type = fields.Selection([('accommodation', 'Accommodation'), ('extension', 'Extension')], string="Residency Type")
    residency_start_date = fields.Date(string="Residency Start Date")
    residency_end_date = fields.Date(string="Residency End Date")
    passport_no = fields.Char(string="Passport No")
    passport_type = fields.Selection([('normal', 'Normal'), ('diplomat', 'Diplomat')], string="Passport Type")
    release_date = fields.Date(string="Release Date")
    end_date = fields.Date(string="End Date")
    release_place = fields.Char(string="Release Place")
    social_affairs_title = fields.Char(string="Social Affairs Title")
    affairs_permit_start_date = fields.Date(string="Affairs Permit Start Date")
    affairs_permit_end_date = fields.Date(string="Affairs Permit End Date")
    affairs_salary = fields.Float(string="Affairs Salary")
    social_contract_id = fields.Many2one('hr.social.contracts', string='Social Contract Name')
    social_contract_no = fields.Char(string='Social Contract Number', related='social_contract_id.contract_no')
    authorized_persons_id = fields.Many2one('social.contracts.authorized.persons', string='Authorized Persons Name')

    is_company_accommodation = fields.Boolean(string="Is Company Accommodation")
    hostel_id = fields.Many2one('hostel', string='Hostel Name')
    floor_id  = fields.Many2one('hostel.floor', string='Floor Number')
    flat_id   = fields.Many2one('hostel.flat' , string='Flat Number')
    room_id   = fields.Many2one('hostel.room' , string='Room Number')
    bed_id    = fields.Many2one('hostel.bed'  , string='Bed Number')

    request_no = fields.Char(string="Request No")
    request_image = fields.Binary(string="Request Image")
    social_start_date = fields.Date(string="Social Start Date")
    due_date = fields.Date(string="Due Date")
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    police_request_no = fields.Char(string="Police Request No")
    police_request_image = fields.Binary(string="Police Request Image")
    arrested = fields.Boolean(string="Arrested")
    requested_by = fields.Many2one('hr.employee', string='Requested By')
    type = fields.Selection([('break', 'Break from work'), ('escape', 'Escape'), ('abstention', 'Abstention From Work'), ('rioter', 'Rioter'), ('another', 'Another')], string='Type')


    def submit_employee_to_hostel(self):
        if self.bed_id:
            self.bed_id.write({'employee_id': self.id})

    def remove_employee_to_hostel(self):
        if self.bed_id:
            self.bed_id.write({'employee_id': False})
            self.hostel_id = self.floor_id = self.flat_id = self.room_id = self.bed_id = False
