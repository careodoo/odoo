# -*- coding: utf-8 -*-
"""Per-client hospitality suppliers.

A client registers the suppliers *they* buy consumables from — and must only
ever see their own list, never the shared Odoo vendor book. We record the owning
client (the commercial partner) on the supplier so the API can scope by it.
"""
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # The client (commercial partner) this supplier was registered for. Set the
    # moment a client adds a supplier from the app; suppliers with no owner are
    # the company's own shared vendors and are never shown to a client.
    hosp_supplier_client_id = fields.Many2one(
        'res.partner', string='مورّد ضيافة لعميل', index=True, tracking=True,
        help='العميل الذي سُجِّل له هذا المورّد. يراه هذا العميل فقط.')
