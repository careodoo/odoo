# -*- coding: utf-8 -*-
from odoo import fields, models, api, _

class HostelBed(models.Model):
    _name = 'hostel.bed'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name         = fields.Char(string='Bed' , track_visibility='onchange', required=True)
    hostel_id    = fields.Many2one('hostel' , string='Hostel', track_visibility='onchange', required=True)
    floor_id     = fields.Many2one('hostel.floor', string='Floor', track_visibility='onchange', required=True)
    flat_id      = fields.Many2one('hostel.flat' , string='Flat' , track_visibility='onchange', required=True)
    room_id      = fields.Many2one('hostel.room' , string='Room' , track_visibility='onchange', required=True)
    employee_id  = fields.Many2one('hr.employee' , string='Employee', track_visibility='onchange')
    vacation     = fields.Selection([('VA', 'Vacation / Available'), ('V', 'Vacation')], string='Vacation')
    start_date   = fields.Date(string='Start Date')
    end_date     = fields.Date(string='End Date')
    is_available = fields.Boolean(string='Available', compute='compute_is_available')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)
    active = fields.Boolean(default=True)

    def compute_is_available(self):
        for record in self:
            if record.employee_id:
                record.is_available = False
            else:
                record.is_available = True

    @api.onchange('floor_id')
    def action_floor_id(self):
        if self.floor_id:
            self.hostel_id = self.floor_id.hostel_id

    @api.onchange('flat_id')
    def action_flat_id(self):
        if self.flat_id:
            self.hostel_id = self.flat_id.hostel_id
            self.floor_id = self.flat_id.floor_id

    @api.onchange('room_id')
    def action_room_id(self):
        if self.room_id:
            self.hostel_id = self.room_id.hostel_id
            self.floor_id  = self.room_id.floor_id
            self.flat_id   = self.room_id.flat_id