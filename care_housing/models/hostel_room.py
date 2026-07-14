# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HostelRoom(models.Model):
    _inherit = 'hostel.room'

    bed_count = fields.Integer(compute='_compute_occupancy', store=True, string='عدد الأسرّة')
    occupied_beds = fields.Integer(compute='_compute_occupancy', store=True, string='مشغولة')
    available_beds = fields.Integer(compute='_compute_occupancy', store=True, string='شاغرة')
    occupancy_pct = fields.Float(compute='_compute_occupancy', store=True, string='نسبة الإشغال %')

    @api.depends('employee_line', 'employee_line.employee_id')
    def _compute_occupancy(self):
        for room in self:
            beds = room.employee_line
            total = len(beds)
            occ = len(beds.filtered(lambda b: b.employee_id))
            room.bed_count = total
            room.occupied_beds = occ
            room.available_beds = total - occ
            room.occupancy_pct = (occ * 100.0 / total) if total else 0.0
