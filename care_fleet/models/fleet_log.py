from odoo import fields, models, api


class FleetVehicleAssignationLog(models.Model):
    _inherit = 'fleet.vehicle.assignation.log'

    damage_ids = fields.Many2many('fleet.damage',
                                  domain="[('vehicle_id', '=', vehicle_id), ('state', '=', 'not_fixed')]")
