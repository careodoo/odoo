from odoo import fields, models, api, _


class ServiceTrip(models.Model):
  _name = 'service.trip'
  _description = 'Service Trip'
  _inherit = ['mail.thread', 'mail.activity.mixin']
  _order = 'id desc'
  _rec_name = 'sequence'

  sequence = fields.Char(
      string='Serial',
      readonly=True,
  )
  reference = fields.Char(string='Reference', compute='_compute_reference')
  pickup_location_id = fields.Many2one(
      'service.pickup.location',
      string='Pickup Location',
  )

  center_id = fields.Many2one(
      'service.center',
      string='Center',
  )

  type_id = fields.Many2one(
      'service.type',
      string='Type',
  )

  trip_tag_ids = fields.Many2many(
      'service.trip.tag',
      string='Tags',
  )

  company_id = fields.Many2one(
      'res.company',
      string='Company',
  )

  project_id = fields.Many2one(
      'service.project',
      string='Project',
  )

  pickuped_datetime = fields.Datetime(string='Pickuped Date & Time')

  contact_id = fields.Many2one(
      'res.partner',
      string='Contact',
  )

  trip_date = fields.Date(string='Trip Date')

  trip_line_ids = fields.One2many(
      'service.trip.line',
      'trip_id',
      string='Items',
  )
  states = fields.Selection(
      [
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

  team_id = fields.Many2one(
      'service.team',
      string='Team',
  )

  total_weight = fields.Float(
      string='Total Weight',
      compute='_compute_total_weight',
  )

  total_quantity = fields.Float(
      string='Total Quantity',
      compute='_compute_total_quantity',
  )
  order_id = fields.Many2one(
      'service.order',
      string='Order',
  )

  def _compute_total_quantity(self):
    for trip in self:
      trip.total_quantity = sum(trip.trip_line_ids.mapped('quantity'))

  def _compute_total_weight(self):
    for trip in self:
      trip.total_weight = sum(trip.trip_line_ids.mapped('weight'))

  @api.model_create_multi
  def create(self, vals_list):
    for vals in vals_list:
      vals['sequence'] = self.env['ir.sequence'].next_by_code('service.trip') or '/'
    return super().create(vals_list)

  def _compute_reference(self):
    for trip in self:
      trip.reference = f"{trip.sequence} - {trip.project_id.sequence}"

  # trip lifecycle
  def action_to_pickuped(self):
    self.write({'states': 'pickuped'})

  def action_to_arrived(self):
    self.write({'states': 'arrived'})

  def action_to_processing(self):
    self.write({'states': 'processing'})

  def action_to_delivered(self):
    self.write({'states': 'delivered'})

  def action_to_completed(self):
    self.write({'states': 'completed'})

  def action_to_cancelled(self):
    self.write({'states': 'cancelled'})

  def action_to_draft(self):
    self.write({'states': 'draft'})

  def action_print_trip_xlsx(self):
    pass

  def action_print_trip_pdf(self):
    pass

  def _get_report_base_filename(self):
    self.ensure_one()
    return '%s' % (self.reference)
