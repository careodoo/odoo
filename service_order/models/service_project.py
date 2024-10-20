from odoo import _, api, fields, models


class ServiceProject(models.Model):
  _name = 'service.project'
  _description = 'Service Project'
  _inherit = ['mail.thread', 'mail.activity.mixin']
  _rec_name = 'name'

  name = fields.Char(required=True)
  active = fields.Boolean(default=True)
  sequence = fields.Char(string='Serial Number', readonly=True)
  state = fields.Selection(
      [
          ('draft', 'Draft'),
          ('valid', 'Valid'),
          ('expired', 'Expired'),
      ],
      default='draft',
      string='Status',
      tracking=True,
  )
  experience_id = fields.Many2one(
      'care.experience',
      string='Experience',
  )
  contact_id = fields.Many2one(
      'res.partner',
      string='Contact',
      tracking=True,
  )
  assign_user_ids = fields.Many2many(
      'res.users',
      string='Assign User',
      tracking=True,
  )

  company_id = fields.Many2one(
      'res.company',
      string='Company',
      tracking=True,
  )

  start_date = fields.Date(
      string='Start Date',
      tracking=True,
  )

  end_date = fields.Date(
      string='End Date',
      tracking=True,
  )

  image = fields.Binary(
      string='Image',
      tracking=True,
  )
  notes = fields.Html(
      string='Notes',
      tracking=True,
  )

  pickup_location_ids = fields.One2many(
      'service.pickup.location',
      'project_id',
      string='Pickup Locations',
      tracking=True,
  )

  team_ids = fields.One2many(
      'service.team',
      'project_id',
      string='Teams',
      tracking=True,
  )

  trip_ids = fields.One2many(
      'service.trip',
      'project_id',
      string='Trips',
      tracking=True,
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
    return {
        'name': _('Pickup Locations'),
        'view_mode': 'tree,form',
        'res_model': 'service.pickup.location',
        'view_id': False,
        'type': 'ir.actions.act_window',
        'domain': [('project_id', '=', self.id)],
    }

  def open_teams(self):
    return {
        'name': _('Teams'),
        'view_mode': 'tree,form',
        'res_model': 'service.team',
        'view_id': False,
        'type': 'ir.actions.act_window',
        'domain': [('project_id', '=', self.id)],
    }

  def open_trips(self):
    return {
        'name': _('Trips'),
        'view_mode': 'tree,form',
        'res_model': 'service.trip',
        'view_id': False,
        'type': 'ir.actions.act_window',
        'domain': [('project_id', '=', self.id)],
    }

  def project_to_draft(self):
    self.write({'state': 'draft'})

  def project_to_valid(self):
    self.write({'state': 'valid'})

  def project_to_expired(self):
    self.write({'state': 'expired'})

  @api.model_create_multi
  def create(self, vals_list):
    for vals in vals_list:
      if 'sequence' not in vals:
        vals['sequence'] = self.env['ir.sequence'].next_by_code('service.project') or '/'
    return super().create(vals_list)
