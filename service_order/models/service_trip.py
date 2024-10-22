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
      tracking=True,
  )

  center_id = fields.Many2one(
      'service.center',
      string='Center',
      tracking=True,
  )

  type_id = fields.Many2one(
      'service.type',
      string='Type',
      tracking=True,
  )

  trip_tag_ids = fields.Many2many(
      'service.trip.tag',
      string='Tags',
      tracking=True,
  )

  company_id = fields.Many2one(
      'res.company',
      string='Company',
      tracking=True,
  )

  project_id = fields.Many2one(
      'service.project',
      string='Project',
      tracking=True,
  )

  pickuped_datetime = fields.Datetime(
      string='Pickuped Date & Time',
      tracking=True,
  )

  contact_id = fields.Many2one(
      'res.partner',
      string='Contact',
      tracking=True,
  )

  trip_date = fields.Date(
      string='Trip Date',
      tracking=True,
  )

  trip_line_ids = fields.One2many(
      'service.trip.line',
      'trip_id',
      string='Items',
  )
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
      tracking=True,
  )

  team_id = fields.Many2one(
      'service.team',
      string='Team',
      tracking=True,
  )

  total_weight = fields.Float(
      string='Total Weight not used',
      compute='_compute_total_weight',
  )

  total_quantity = fields.Float(
      string='Total Quantity',
      compute='_compute_total_quantity',
  )
  total_qty_weight = fields.Float(
      string='Total Weight',
      compute='_compute_total_qty_weight',
  )

  order_id = fields.Many2one(
      'service.order',
      string='Order',
  )
  active = fields.Boolean(default=True)

  def _compute_total_qty_weight(self):
    for trip in self:
      trip.total_qty_weight = sum([line.quantity * line.weight for line in trip.trip_line_ids])

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
    self.order_id.states = 'pickuped'

  def action_to_arrived(self):
    self.write({'states': 'arrived'})
    self.order_id.states = 'arrived'

  def action_to_processing(self):
    self.write({'states': 'processing'})
    self.order_id.states = 'processing'

  def action_to_delivered(self):
    self.write({'states': 'delivered'})
    self.order_id.states = 'delivered'

  def action_to_completed(self):
    self.write({'states': 'completed'})
    self.order_id.states = 'completed'

  def action_to_cancelled(self):
    self.write({'states': 'cancelled'})
    self.order_id.states = 'cancelled'

  def action_to_draft(self):
    self.write({'states': 'draft'})
    self.order_id.states = 'draft'

  def action_to_scheduled(self):
    self.write({'states': 'scheduled'})

  def _get_report_base_filename(self):
    self.ensure_one()
    return '%s' % (self.reference)

  # send email to contact person including report
  def action_send_email(self):
    self.ensure_one()
    template_id = self.env.ref('service_order.mail_template_trip_report').id
    lang = self.env.context.get('lang')
    template = self.env['mail.template'].browse(template_id)
    if template.lang:
      lang = template._render_lang(self.ids)[self.id]
    ctx = {
        'default_model': 'service.trip',
        'default_res_id': self.ids[0],
        'default_use_template': bool(template_id),
        'default_template_id': template_id,
        'default_composition_mode': 'comment',
        'custom_layout': "mail.mail_notification_paynow",
        'proforma': self.env.context.get('proforma', False),
        'force_email': True,
        'model_description': self.with_context(lang=lang).sequence,
    }
    return {
        'type': 'ir.actions.act_window',
        'view_mode': 'form',
        'res_model': 'mail.compose.message',
        'views': [(False, 'form')],
        'view_id': False,
        'target': 'new',
        'context': ctx,
    }
