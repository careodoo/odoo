from odoo import api, fields, models, _


class SecurityPostSite(models.Model):
    _name = 'security.post.site'
    _description = 'Security Post Site'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code')
    client_id = fields.Many2one('security.client', string='Client', required=True)
    premise_id = fields.Many2one('security.premise', string='Premise')
    location_id = fields.Many2one('security.location', string='Location')
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)

    # Required personnel
    guard_count = fields.Integer(string='Required Guards', default=1)
    supervisor_required = fields.Boolean(string='Supervisor Required', default=False)

    # Schedule information
    operating_hours = fields.Selection([
        ('24_7', '24/7'),
        ('day_only', 'Day Shift Only'),
        ('night_only', 'Night Shift Only'),
        ('custom', 'Custom Hours')
    ], string='Operating Hours', default='24_7')

    start_time = fields.Float(string='Start Time')
    end_time = fields.Float(string='End Time')

    # Equipment
    equipment_ids = fields.Many2many('security.equipment', string='Required Equipment')

    # Assignments
    assignment_ids = fields.One2many('security.post.assignment', 'post_site_id', string='Assignments')
    assignment_count = fields.Integer(compute='_compute_assignment_count', string='Assignment Count')

    @api.depends('assignment_ids')
    def _compute_assignment_count(self):
        for post in self:
            post.assignment_count = len(post.assignment_ids)

    def action_view_assignments(self):
        self.ensure_one()
        return {
            'name': _('Post Assignments'),
            'type': 'ir.actions.act_window',
            'res_model': 'security.post.assignment',
            'view_mode': 'tree,form',
            'domain': [('post_site_id', '=', self.id)],
            'context': {'default_post_site_id': self.id},
        }
