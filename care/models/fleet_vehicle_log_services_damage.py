# -*- coding: utf-8 -*-
from odoo import fields, models, api, _

class FleetVehicleLogServices(models.Model):
    _name = 'fleet.vehicle.log.services.damage'
    _order = 'id desc'

    name        = fields.Char(string="Name", required=True)
    description = fields.Char(string="How To", required=True)
    source      = fields.Selection([('purchase', 'Purchase'), ('purchase_scrap', 'Purchase From Scrap'),
                                    ('stock', 'From Stock'), ('lathe', 'Lathe'), ('maintenance', 'Maintenance')], string="Source", required=True)
    purchase_id = fields.Many2one('purchase.order')
    purchase_amount_total = fields.Monetary(string='Purchase Total', related='purchase_id.amount_total', store=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
    cost        = fields.Float(string="Cost", required=True)
    is_purchase = fields.Boolean(string="Is Purchase")
    service_id  = fields.Many2one('fleet.vehicle.log.services', string="Service")
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)