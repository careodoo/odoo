# -*- coding: utf-8 -*-
from odoo import fields, models, api, _

class HostelFloor(models.Model):
    _name = 'hostel.floor'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name      = fields.Char(string='Name', track_visibility='onchange', required=True)
    hostel_id = fields.Many2one('hostel' , string='Hostel', track_visibility='onchange', required=True)
    employee_line = fields.One2many('hostel.bed', 'floor_id', string="Employee Line", readonly=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)
    active = fields.Boolean(default=True)