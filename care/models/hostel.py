# -*- coding: utf-8 -*-
from odoo import fields, models, api, _

class Hostel(models.Model):
    _name = 'hostel'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name          = fields.Char(string='Name', track_visibility='onchange', required=True)
    floor_count   = fields.Integer(string='Floor Count', compute="compute_hostel_info")
    flat_count    = fields.Integer(string='Flat Count', compute="compute_hostel_info")
    room_count    = fields.Integer(string='Room Count', compute="compute_hostel_info")
    bed_count     = fields.Integer(string='Bed Count / Capacity', compute="compute_hostel_info")
    used_places   = fields.Integer(string='Used Places' , compute="compute_hostel_info")
    availability  = fields.Integer(string='Availability', compute="compute_hostel_info")
    maintenance   = fields.Integer(string='Maintenance' , compute="compute_hostel_info")
    address       = fields.Char(string='Address', track_visibility='onchange', required=True)
    price         = fields.Float(string="Price" , track_visibility='onchange', required=True)
    labor_cost    = fields.Float(string="Labor Cost", track_visibility='onchange', required=True, compute="compute_labor_cost")
    employee_line = fields.One2many('hostel.bed', 'hostel_id', string="Employee Line", readonly=True)
    total_capacity= fields.Integer(string="Total Capacity")
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)

    def compute_labor_cost(self):
        for record in self:
            if record.used_places == 0:
                record.labor_cost = record.price
            else:
                record.labor_cost = record.price / record.used_places
    def compute_hostel_info(self):
        for record in self:
            record.floor_count  = len(self.env['hostel.floor'].search([('hostel_id', '=', record.id)]))
            record.flat_count   = len(self.env['hostel.flat'].search([('hostel_id', '=', record.id)]))
            record.room_count   = len(self.env['hostel.room'].search([('hostel_id', '=', record.id)]))
            record.bed_count    = len(self.env['hostel.bed'].search([('hostel_id', '=', record.id)]))
            record.used_places  = 0
            record.availability = 0
            record.maintenance  = len(self.env['hostel.maintenance'].search([('hostel_id', '=', record.id), ('is_active', '=', True)]))
            for line in record.employee_line:
                if line.is_available:
                    record.availability += 1
                else:
                    record.used_places += 1


    def action_availability_show(self):
        return {
            'name': _('Availability'),
            'view_mode': 'tree,form',
            'res_model': 'hostel.bed',
            'type': 'ir.actions.act_window',
            'domain': [('hostel_id', '=', self.id), ('employee_id', '=', False)]
        }

    def action_used_place_show(self):
        return {
            'name': _('Used Places'),
            'view_mode': 'tree,form',
            'res_model': 'hostel.bed',
            'type': 'ir.actions.act_window',
            'domain': [('hostel_id', '=', self.id), ('employee_id', '!=', False)]
        }

    def action_floor_show(self):
        return {
            'name': _('Floor'),
            'view_mode': 'tree,form',
            'res_model': 'hostel.floor',
            'type': 'ir.actions.act_window',
            'domain': [('hostel_id', '=', self.id)]
        }

    def action_flat_show(self):
        return {
            'name': _('Flats'),
            'view_mode': 'tree,form',
            'res_model': 'hostel.flat',
            'type': 'ir.actions.act_window',
            'domain': [('hostel_id', '=', self.id)]
        }

    def action_room_show(self):
        return {
            'name': _('Rooms'),
            'view_mode': 'list,form',
            'res_model': 'hostel.room',
            'type': 'ir.actions.act_window',
            'domain': [('hostel_id', '=', self.id)]
        }

    def action_bed_show(self):
        return {
            'name': _('Beds'),
            'view_mode': 'list,form',
            'res_model': 'hostel.bed',
            'type': 'ir.actions.act_window',
            'domain': [('hostel_id', '=', self.id)]
        }

    def action_maintenance_show(self):
        return {
            'name': _('Maintenance'),
            'view_mode': 'list,form',
            'res_model': 'hostel.maintenance',
            'type': 'ir.actions.act_window',
            'domain': [('hostel_id', '=', self.id)]
        }