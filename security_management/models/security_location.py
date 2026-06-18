from odoo import api, fields, models, _


class SecurityLocation(models.Model):
    _name = 'security.location'
    _description = 'Security Location'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code')
    premise_id = fields.Many2one('security.premise', string='Premise')
    floor_id = fields.Many2one('security.floor', string='Floor')
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)

    # Coordinates for map display
    latitude = fields.Float(string='Latitude', digits=(16, 8))
    longitude = fields.Float(string='Longitude', digits=(16, 8))

    # For patrol points
    patrol_point_ids = fields.One2many('security.patrol.point', 'location_id', string='Patrol Points')
    patrol_point_count = fields.Integer(compute='_compute_patrol_point_count', string='Patrol Points')

    @api.depends('patrol_point_ids')
    def _compute_patrol_point_count(self):
        for location in self:
            location.patrol_point_count = len(location.patrol_point_ids)

    def action_view_patrol_points(self):
        self.ensure_one()
        return {
            'name': _('Patrol Points'),
            'type': 'ir.actions.act_window',
            'res_model': 'security.patrol.point',
            'view_mode': 'tree,form',
            'domain': [('location_id', '=', self.id)],
            'context': {'default_location_id': self.id},
        }
