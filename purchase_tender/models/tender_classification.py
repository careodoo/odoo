# -*- coding: utf-8 -*-
from odoo import fields, models


class PurchaseTenderClassification(models.Model):
    """Tender business-line classification (cleaning / security / agriculture /
    other). A catalog so new classifications can be added freely."""
    _name = 'purchase.tender.classification'
    _description = 'Tender Classification'
    _order = 'sequence, name'

    name = fields.Char(string='التصنيف', required=True, translate=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer(string='Color')
    active = fields.Boolean(default=True)
    tender_count = fields.Integer(string='Tenders', compute='_compute_tender_count')

    def _compute_tender_count(self):
        data = self.env['purchase.tender']._read_group(
            [('classification_id', 'in', self.ids)], ['classification_id'], ['__count'])
        counts = {c.id: n for c, n in data}
        for r in self:
            r.tender_count = counts.get(r.id, 0)
