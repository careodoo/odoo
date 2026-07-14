# -*- coding: utf-8 -*-
# Bridge added here (NOT in care_experience) on purpose: purchase_tender depends
# on care_experience, so declaring the reverse tender_id link here avoids a
# circular module dependency. Government contracts are priced from a tender;
# commercial ones from a proposal (handled in care_experience itself).
from odoo import models, fields, api, _


class CareExperience(models.Model):
    _inherit = 'care.experience'

    tender_id = fields.Many2one(
        'purchase.tender', string='المناقصة (التسعير الحكومي)', tracking=True,
        help='مصدر تسعير العقود الحكومية: المناقصة المرتبطة في موديول المناقصات.')

    @api.depends('contract_type', 'tender_id', 'tender_id.price', 'tender_id.our_price',
                 'proposal_id', 'proposal_id.total_amount', 'contract_amount')
    def _compute_pricing(self):
        # Extend the base computation: fill tender pricing for government
        # contracts, then defer to super() for the commercial/proposal path.
        gov = self.filtered(lambda r: r.contract_type == 'government' and r.tender_id)
        for rec in gov:
            rec.pricing_ref = rec.tender_id.display_name
            rec.pricing_value = rec.tender_id.our_price or rec.tender_id.price or rec.contract_amount
        super(CareExperience, self - gov)._compute_pricing()
