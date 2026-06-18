from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SecurityShiftType(models.Model):
    _name = 'security.shift.type'
    _description = 'Security Shift Type'
    _order = 'sequence, name'
    
    name = fields.Char(string='Shift Name', required=True)
    code = fields.Char(string='Shift Code', required=True)
    start_time = fields.Float(string='Start Time', required=True)
    end_time = fields.Float(string='End Time', required=True)
    color = fields.Char(string='Color', default='#007bff')
    is_24h = fields.Boolean(string='Is 24 Hour Shift', default=False)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)
    duration = fields.Float(string='Duration', compute='_compute_duration')
    is_night_shift = fields.Boolean(string='Is Night Shift', default=False)
    description = fields.Text(string='Description')
    
    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for record in self:
            if record.end_time >= record.start_time:
                record.duration = record.end_time - record.start_time
            else:
                # Handle overnight shifts (e.g., 22:00 to 06:00)
                record.duration = (24 - record.start_time) + record.end_time
    
    _sql_constraints = [
        ('code_uniq', 'UNIQUE(code)', 'Shift code must be unique!')
    ]
    
    @api.constrains('start_time', 'end_time')
    def _check_times(self):
        for record in self:
            if record.start_time < 0 or record.start_time >= 24:
                raise ValidationError(_("Start time must be between 0:00 and 23:59"))
            if record.end_time < 0 or record.end_time >= 24:
                raise ValidationError(_("End time must be between 0:00 and 23:59"))
            if record.start_time == record.end_time and not record.is_24h:
                raise ValidationError(_("Start time and end time cannot be the same unless it's a 24-hour shift"))
    
    @api.onchange('is_24h')
    def _onchange_is_24h(self):
        if self.is_24h:
            self.start_time = 0.0
            self.end_time = 0.0
            self.duration = 24.0