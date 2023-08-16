# -*- coding: utf-8 -*-

from odoo import models, fields, api


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    damage_count = fields.Integer(compute="_compute_damage", string="Damage Count")
    driver_type = fields.Selection(selection=[
        ('employee', 'Employee'), ('contact', 'Contact')
    ], default='employee')
    driver_employee_id = fields.Many2one(
        'hr.employee', 'Driver (Employee)',
        compute=False, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", tracking=True)

    # @api.onchange('driver_id')
    # def onchange_driver_id(self):
    #     for vehicle in self:
    #         if vehicle.driver_id:
    #             vehicle.driver_employee_id = self.env['hr.employee'].search([
    #                 ('address_home_id', '=', vehicle.driver_id.id),
    #             ], limit=1)
    #
    # @api.onchange('driver_employee_id')
    # def onchange_driver_employee_id(self):
    #     for vehicle in self:
    #         if vehicle.driver_employee_id:
    #             vehicle.driver_id = vehicle.driver_employee_id.address_home_id.id

    def _compute_damage(self):
        for record in self:
            record.damage_count = self.env['fleet.damage'].search_count([('vehicle_id', '=', record.id)])

    def open_damages(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Damages',
            'view_mode': 'tree',
            'res_model': 'fleet.damage',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id}
        }


