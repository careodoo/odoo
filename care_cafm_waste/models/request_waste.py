# -*- coding: utf-8 -*-
"""What a collection request is actually carrying.

These fields live here, not in care_cafm, because they point at
cafm.waste.type and cafm.waste.item — models this module owns. Declaring a
many2many in a module that cannot see the target leaves its relation table
uncreated, and the first save fails on a missing table.
"""
from odoo import api, fields, models


class ServiceRequestWaste(models.Model):
    _inherit = 'care.cafm.service.request'

    # A crew arriving with the wrong vehicle for a load of scrap metal is a
    # wasted trip, so the client says what it is up front. Saying nothing is a
    # legitimate answer — most collections are ordinary mixed waste — so the
    # default is "general" rather than an empty required field.
    waste_scope = fields.Selection([
        ('general', 'General — Mixed Waste'),
        ('type', 'Specific Category'),
        ('items', 'Specific Items'),
    ], string='Load Scope', default='general', tracking=True)
    waste_type_id = fields.Many2one('cafm.waste.type', string='Load Category',
                                    tracking=True)
    waste_item_ids = fields.Many2many('cafm.waste.item', string='Items To Be Transported')
    waste_note = fields.Char(string='Load Description',
                             help='Used when the available categories do not cover what will be transported.')
    waste_summary = fields.Char(string='Load Summary', compute='_compute_waste_summary',
                                store=True)

    @api.depends('waste_scope', 'waste_type_id', 'waste_item_ids', 'waste_note')
    def _compute_waste_summary(self):
        for r in self:
            if r.waste_scope == 'type' and r.waste_type_id:
                r.waste_summary = r.waste_type_id.name
            elif r.waste_scope == 'items' and r.waste_item_ids:
                r.waste_summary = ', '.join(r.waste_item_ids.mapped('name')[:6])
            else:
                r.waste_summary = r.waste_note or 'General'

