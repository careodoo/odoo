from odoo import _, api, fields, models


class ServiceCenterTag(models.Model):
  _name = 'service.center.tag'
  _description = 'Service Center Tag'
  _order = 'name'

  name = fields.Char(required=True)
  color = fields.Integer(string='Color')
