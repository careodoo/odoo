# -*- coding: utf-8 -*-
from odoo import fields, models, api, _

class HostelFlat(models.Model):
    _name = 'hostel.flat'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name      = fields.Char(string='Name', track_visibility='onchange', required=True)
    hostel_id = fields.Many2one('hostel' , string='Hostel', track_visibility='onchange', required=True)
    floor_id  = fields.Many2one('hostel.floor', string='Floor', track_visibility='onchange', required=True)
    employee_line = fields.One2many('hostel.bed', 'flat_id', string="Employee Line", readonly=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)

    @api.onchange('floor_id')
    def action_floor_id(self):
        if self.floor_id:
            self.hostel_id = self.floor_id.hostel_id