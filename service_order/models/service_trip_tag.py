from odoo import _, api, fields, models


class ServiceTripTag(models.Model):
  _name = 'service.trip.tag'
  _description = 'Service Trip Tag'
  _order = 'name'

  name = fields.Char(required=True)
  color = fields.Integer(string='Color')
