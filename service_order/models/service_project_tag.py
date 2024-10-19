from odoo import _, api, fields, models


class ServiceProjectTag(models.Model):
  _name = 'service.project.tag'
  _description = 'Service Project Tag'
  _order = 'name'

  name = fields.Char(required=True)
  color = fields.Integer(string='Color')
  active = fields.Boolean(default=True)