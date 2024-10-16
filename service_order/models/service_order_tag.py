from odoo import _, api, fields, models


class ServiceOrderTag(models.Model):
  _name = 'service.order.tag'
  _description = 'Service Order Tag'
  _order = 'name'

  name = fields.Char(required=True)
  color = fields.Integer(string='Color')
