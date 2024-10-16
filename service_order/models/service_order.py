from odoo import  fields, models, api


class ServiceOrder(models.Model):
  _name = 'service.order'
  _description = 'Service Order'
  _inherit = ['mail.thread', 'mail.activity.mixin']
  _order = 'id desc'
  _rec_name = 'serial'

  serial = fields.Char(string='Serial')
  project_id = fields.Many2one(
      'service.project',
      string='Project',
  )

  type_id = fields.Many2one(
      'service.type',
      string='Type',
  )

  pickup_location_id = fields.Many2one(
      'service.pickup.location',
      string='Pickup Location',
  )

  order_datetime = fields.Datetime(string='Order Date & Time')

  notes = fields.Html(string='Notes')

  states = fields.Selection(
      [
          ('scheduled', 'Scheduled'),
          ('draft', 'Draft'),
          ('pickuped', 'Pickuped'),
          ('arrived', 'Arrived'),
          ('processing', 'Processing'),
          ('delivered', 'Delivered'),
          ('completed', 'Completed'),
          ('cancelled', 'Cancelled'),
      ],
      string='State',
      default='draft',
  )

  @api.model_create_multi
  def create(self, vals_list):
    for vals in vals_list:
      vals['serial'] = self.env['ir.sequence'].next_by_code('service.order') or '/'
    return super().create(vals_list)


