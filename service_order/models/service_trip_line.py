from odoo import _, api, fields, models

class ServiceTripLine(models.Model):
  _name = 'service.trip.line'
  _description = 'Service Trip Line'
  _order = 'id'

  trip_id = fields.Many2one(
      'service.trip',
      string='Service Trip',
  )

  item_id = fields.Many2one(
      'service.item',
      string='Service Item',
  )
  active = fields.Boolean(default=True)
  width = fields.Float(related = 'item_id.width', string='Width')
  height = fields.Float(related = 'item_id.height', string='Height')
  weight = fields.Float(related = 'item_id.weight', string='Weight')
  quantity = fields.Float(string='Quantity')

