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

  trips_counter = fields.Integer(
      string='Trips Counter',
      compute='_compute_trips_counter',
  )
  active = fields.Boolean(default=True)

  def _compute_trips_counter(self):
    for item in self:
      item.trips_counter = self.env['service.trip'].search_count([(
          'trip_line_ids.item_id',
          'in',
          item.ids,
      )])

  def open_trips_action(self):
    return {
        'name': _('Trips'),
        'type': 'ir.actions.act_window',
        'res_model': 'service.trip',
        'view_mode': 'tree,form',
        'domain': [('trip_line_ids.item_id', 'in', self.ids)],
    }
