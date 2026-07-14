# -*- coding: utf-8 -*-
# The CAFM asset register IS the accounting fixed-asset register (account.asset).
# We only add an operational layer (facility/location/QR) on the SAME record —
# no duplicate asset list.
from odoo import fields, models, api, _


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    cafm_facility_id = fields.Many2one('care.cafm.facility', string='المرفق (تشغيل)', index=True)
    cafm_location_id = fields.Many2one('care.cafm.location', string='الموقع (تشغيل)',
                                       domain="[('facility_id','=',cafm_facility_id)]")
    cafm_criticality = fields.Selection([
        ('low', 'منخفضة'), ('medium', 'متوسطة'), ('high', 'حرجة'),
    ], string='الحرجية', default='medium')
    cafm_workorder_ids = fields.One2many('care.cafm.workorder', 'asset_id', string='أوامر الصيانة')
    cafm_wo_count = fields.Integer(compute='_compute_cafm_wo')

    def _compute_cafm_wo(self):
        for rec in self:
            rec.cafm_wo_count = len(rec.cafm_workorder_ids)
