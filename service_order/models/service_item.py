from odoo import _, api, fields, models


class ServiceItem(models.Model):
  _name = 'service.item'
  _description = 'Service Item'
  _inherit = ['mail.thread', 'mail.activity.mixin']

  name = fields.Char(required=True)
  image = fields.Binary(string='Image')
  company_id = fields.Many2one(
      'res.company',
      string='Company',
  )

  type_id = fields.Many2one(
      'service.type',
      string='Service Type',
  )

  notes = fields.Html(string='Notes')

  width = fields.Float(string='Width')

  height = fields.Float(string='Height')

  weight = fields.Float(string='Weight')

  item_tag_ids = fields.Many2many(
      'service.item.tag',
      string='Tags',
  )