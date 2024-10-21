from odoo import fields, models, api


class ServiceOrder(models.Model):
  _name = 'service.order'
  _description = 'Service Order'
  _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
  _order = 'id desc'
  _rec_name = 'serial'

  serial = fields.Char(
      string='Serial',
      readonly=True,
  )

  active = fields.Boolean(default=True)
  project_id = fields.Many2one(
      'service.project',
      string='Project',
      tracking=True,
  )

  type_id = fields.Many2one(
      'service.type',
      string='Type',
      tracking=True,
  )

  pickup_location_id = fields.Many2one(
      'service.pickup.location',
      string='Pickup Location',
      tracking=True,
  )

  order_datetime = fields.Datetime(
      string='Order Date & Time',
      tracking=True,
  )

  notes = fields.Html(string='Notes')

  states = fields.Selection(
      [
          ('draft', 'Draft'),
          ('scheduled', 'Scheduled'),
          ('pickuped', 'Pickuped'),
          ('arrived', 'Arrived'),
          ('processing', 'Processing'),
          ('delivered', 'Delivered'),
          ('completed', 'Completed'),
          ('cancelled', 'Cancelled'),
      ],
      string='State',
      default='draft',
      copy=False,
      tracking=True,
  )
  order_line_ids = fields.One2many(
      'service.order.line',
      'order_id',
      string='Items',
  )
  trip_line_ids = fields.One2many(
      'service.trip.line',
      'order_id',
      related='trip_id.trip_line_ids',
      string='Items',
      tracking=True,
  )
  trip_id = fields.Many2one(
      'service.trip',
      string='Trip',
      tracking=True,
  )
  qr_url = fields.Char(
      string='QR Code URL',
      compute='_compute_qr_url',
  )

  @api.model_create_multi
  def create(self, vals_list):
    for vals in vals_list:
      vals['serial'] = self.env['ir.sequence'].next_by_code('service.order') or '/'
    # send activity
    resutl = super().create(vals_list)
    self.env['mail.activity'].sudo().create({
        'res_id': resutl.id,
        'res_model_id': self.env['ir.model']._get('service.order').id,
        'summary': 'New Service Order',
        'note': 'New Service Order',
        'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
    })
    return resutl

  def action_to_schedule(self):
    self.write({'states': 'scheduled'})

  def action_to_cancelled(self):
    self.write({'states': 'cancelled'})

  def action_to_draft(self):
    self.write({'states': 'draft'})

  def convert_to_trip(self):
    trip = self.env['service.trip'].create({
        'project_id': self.project_id.id,
        'type_id': self.type_id.id,
        'pickup_location_id': self.pickup_location_id.id,
        'pickuped_datetime': self.order_datetime,
        'states': 'draft',
        'trip_line_ids': [(0, 0, {
            'item_id': line.item_id.id,
            'quantity': line.quantity,
        }) for line in self.order_line_ids],
        'order_id': self.id,
    })
    self.write({'trip_id': trip.id})
    self.action_to_schedule()

  def _compute_access_url(self):
    super()._compute_access_url()
    for order in self:
      order.access_url = '/service_order/%s' % (order.id)

  def _compute_qr_url(self):
    for order in self:
      order.qr_url = self.get_base_url() + order.access_url

  def _get_report_base_filename(self):
    self.ensure_one()
    return '%s' % (self.trip_id.reference)
