# -*- coding: utf-8 -*-
from odoo import fields, models, api, _

class HostelMaintenance(models.Model):
    _name = 'hostel.maintenance'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name      = fields.Char(string='Name', tracking=True, required=True)
    hostel_id = fields.Many2one('hostel' , string='Hostel', tracking=True, required=True)
    floor_id  = fields.Many2one('hostel.floor', string='Floor', tracking=True, required=True)
    flat_id   = fields.Many2one('hostel.flat' , string='Flat' , tracking=True, required=True)
    room_id   = fields.Many2one('hostel.room' , string='Room' , tracking=True, required=True)
    expected_cost = fields.Float(string='Expected Cost' , tracking=True, required=True)
    actually_cost = fields.Float(string='Actually Cost' , tracking=True, required=True)
    is_active     = fields.Boolean(string='Active', default=True)
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)

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
            self.floor_id = self.room_id.floor_id
            self.flat_id = self.room_id.flat_id