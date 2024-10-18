from odoo import _, api, fields, models


class ServiceOrderLine(models.Model):
  _name = 'service.order.line'
  _description = 'Service Order Line'
  _order = 'id'

  order_id = fields.Many2one(
      'service.order',
      string='Service Order',
  )

  item_id = fields.Many2one(
      'service.item',
      string='Service Item',
  )
  width = fields.Float(related='item_id.width', string='Width')
  height = fields.Float(related='item_id.height', string='Height')
  weight = fields.Float(related='item_id.weight', string='Weight')
  quantity = fields.Float(string='Quantity')
