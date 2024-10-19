from odoo import fields, models


class ServicePickupLocation(models.Model):
  _name = 'service.pickup.location'
  _description = 'Service Pickup Location'

  name = fields.Char(required=True)
  pickup_location_tag_ids = fields.Many2many(
      'service.pickup.location.tag',
      string='Tags',
  )
  active = fields.Boolean(default=True)
  address = fields.Char(string='Address')
  project_id = fields.Many2one(
      'service.project',
      string='Project',
  )

  state = fields.Selection(
      [
          ('capital', 'Capital'),
          ('hawali', 'Hawali'),
          ('ahmadi', 'Ahmadi'),
          ('jahara', 'Jahara'),
          ('mubarak_al_kabeer', 'Mubarak Al-Kabeer'),
      ],
      string='State',
  )
  project_ids = fields.Many2many(
      'service.project',
      string='Projects',
  )
