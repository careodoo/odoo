from odoo import  fields, models


class ServiceTeam(models.Model):
  _name = 'service.team'
  _description = 'Service Team'

  name = fields.Char(required=True)
  company_id = fields.Many2one(
      'res.company',
      string='Company',
  )
  active = fields.Boolean(default=True)
  project_id = fields.Many2one(
      'service.project',
      string='Service Project',
  )

  working_mode = fields.Selection(
      [
          ('temporary', 'Temporary'),
          ('permanent', 'Permanent'),
          ('mixed', 'Mixed'),
      ],
      default='temporary',
      string='Working Mode',
  )

  notes = fields.Html(string='Notes')

  employee_ids = fields.Many2many(
      'hr.employee',
      string='Employees',
  )
