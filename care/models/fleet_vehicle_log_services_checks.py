# -*- coding: utf-8 -*-
from odoo import fields, models, api, _

class FleetVehicleLogServicesChecks(models.Model):
    _name = 'fleet.vehicle.log.services.checks'
    _order = 'id desc'

    name  = fields.Many2one('services.checks', string="Name", required=True)
    service_id  = fields.Many2one('fleet.vehicle.log.services', string="Service")
    state = fields.Boolean(string="State")
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)
    active = fields.Boolean(default=True)


class ServicesChecks(models.Model):
    _name = 'services.checks'
    _order = 'id desc'

    name  = fields.Char(string="Name", required=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)
    active = fields.Boolean(default=True)
