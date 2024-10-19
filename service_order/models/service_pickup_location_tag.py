from odoo import _, api, fields, models


class ServicePickupLocationTag(models.Model):
  _name = 'service.pickup.location.tag'
  _description = 'Service Pickup Location Tag'
  _order = 'name'

  name = fields.Char(required=True)
  color = fields.Integer(string='Color')
  active = fields.Boolean(default=True)