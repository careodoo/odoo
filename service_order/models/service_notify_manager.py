from odoo import _, api, fields, models

class ServiceNotifyManager(models.Model):
  _name = 'service.notify.manager'
  _description = 'Service Notify Manager'
  _inherit = ['mail.thread', 'mail.activity.mixin']
  _order = 'id desc'

  user_ids = fields.Many2many(
      'res.users',
      string='Users',
  )

  state = fields.Selection(
    selection= lambda self: self.env['service.trip']._fields['states'].selection,
    string='State',
  )

  _sql_constraints = [
    ('unique_state', 'unique(state)', 'State already exists!'),
  ]

