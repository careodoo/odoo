# -*- coding: utf-8 -*-
from odoo import fields, models


class CareViolationType(models.Model):
    """Catalogue of traffic violation types (each with its fine amount)."""
    _name = 'care.violation.type'
    _description = 'Traffic Violation Type'
    _order = 'sequence, name'

    name = fields.Char(string='Violation', required=True, translate=True)
    amount = fields.Monetary(string='Fine Amount')
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    legacy_id = fields.Integer(index=True, copy=False)
