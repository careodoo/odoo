# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    housing_bed_ids = fields.One2many('hostel.bed', 'employee_id', string='الأسرّة')
    housing_bed_id = fields.Many2one('hostel.bed', compute='_compute_housing', store=True, string='السرير')
    housing_room_id = fields.Many2one('hostel.room', compute='_compute_housing', store=True, string='الغرفة')
    housing_hostel_id = fields.Many2one(related='housing_bed_id.hostel_id', store=True, string='السكن')
    housing_floor_id = fields.Many2one(related='housing_bed_id.floor_id', store=True, string='الطابق')

    @api.depends('housing_bed_ids')
    def _compute_housing(self):
        for emp in self:
            bed = emp.housing_bed_ids[:1]
            emp.housing_bed_id = bed.id
            emp.housing_room_id = bed.room_id.id if bed else False
