from odoo import _, api, fields, models


class ServiceProject(models.Model):
  _name = 'service.project'
  _description = 'Service Project'
  _inherit = ['mail.thread', 'mail.activity.mixin']

  name = fields.Char(required=True)
  sequence = fields.Char(string='Serial Number', readonly=True)
  state = fields.Selection(
      [
          ('draft', 'Draft'),
          ('valid', 'Valid'),
          ('expired', 'Expired'),
      ],
      default='draft',
      string='Status',
  )
  contact_id = fields.Many2one(
      'res.partner',
      string='Contact',
  )
  assign_user_id = fields.Many2one(
      'res.users',
      string='Assign User',
  )

  company_id = fields.Many2one(
      'res.company',
      string='Company',
  )

  start_date = fields.Date(string='Start Date',)

  end_date = fields.Date(string='End Date',)

  image = fields.Binary(string='Image',)
  notes = fields.Html(string='Notes',)

  pickup_location_ids = fields.One2many(
      'service.pickup.location',
      'project_id',
      string='Pickup Locations',
  )

  team_ids = fields.One2many(
      'service.team',
      'project_id',
      string='Teams',
  )

  trip_ids = fields.One2many(
      'service.trip',
      'project_id',
      string='Trips',
  )

  pickup_location_ids_count = fields.Integer(
      string='Pickup Locations Count',
      compute='_compute_pickup_location_ids_count',
  )

  team_ids_count = fields.Integer(
      string='Teams Count',
      compute='_compute_team_ids_count',
  )

  trip_ids_count = fields.Integer(
      string='Trips Count',
      compute='_compute_trip_ids_count',
  )

  def _compute_pickup_location_ids_count(self):
    for record in self:
      record.pickup_location_ids_count = len(record.pickup_location_ids)

  def _compute_team_ids_count(self):
    for record in self:
      record.team_ids_count = len(record.team_ids)

  def _compute_trip_ids_count(self):
    for record in self:
      record.trip_ids_count = len(record.trip_ids)


  def open_locations(self):
    pass

  def open_teams(self):
    pass

  def open_trips(self):
    pass

  def project_to_draft(self):
    pass

  def project_to_valid(self):
    pass

  def project_to_expired(self):
    pass


  @api.model_create_multi
  def create(self, vals_list):
    for vals in vals_list:
      if 'sequence' not in vals:
        vals['sequence'] = self.env['ir.sequence'].next_by_code('service.project') or '/'
    return super().create(vals_list)