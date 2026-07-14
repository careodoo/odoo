# -*- coding: utf-8 -*-
from odoo import fields, models, api


class Hostel(models.Model):
    """Occupancy percentage for the hostel dashboard (care_hr depends on care,
    which defines the hostel model)."""
    _inherit = 'hostel'

    occupancy_pct = fields.Float(string='Occupancy %', compute='_compute_occupancy_pct', store=True)
    occupancy_band = fields.Selection([
        ('low', 'Low (<60%)'), ('mid', 'Medium (60-90%)'), ('high', 'High (>90%)'),
    ], string='Occupancy Band', compute='_compute_occupancy_pct', store=True)

    @api.depends('used_places', 'total_capacity')
    def _compute_occupancy_pct(self):
        for h in self:
            pct = round((h.used_places or 0) / h.total_capacity * 100, 1) if h.total_capacity else 0.0
            h.occupancy_pct = pct
            h.occupancy_band = 'low' if pct < 60 else ('high' if pct > 90 else 'mid')
