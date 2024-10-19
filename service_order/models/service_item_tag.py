from odoo import _, api, fields, models


class ServiceItemTag(models.Model):
  _name = 'service.item.tag'
  _description = 'Service Item Tag'
  _order = 'name'

  name = fields.Char(required=True)
  color = fields.Integer(string='Color')
  active = fields.Boolean(default=True)