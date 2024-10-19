from odoo import _, api, fields, models


class ServiceCenter(models.Model):
  _name = 'service.center'
  _description = 'Service Center'

  name = fields.Char(required=True)
  center_tag_ids = fields.Many2many(
      'service.center.tag',
      string='Tags',
  )

  company_id = fields.Many2one(
      'res.company',
      string='Company',
  )
  active = fields.Boolean(default=True)