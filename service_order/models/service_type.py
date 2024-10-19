from odoo import _, api, fields, models


class ServiceType(models.Model):
  _name = 'service.type'
  _description = 'Service Type'

  name = fields.Char(required=True)
  active = fields.Boolean(default=True)