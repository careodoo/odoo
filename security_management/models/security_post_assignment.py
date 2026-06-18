from odoo import api, fields, models, _
from datetime import datetime, timedelta


class SecurityPostAssignment(models.Model):
    _name = 'security.post.assignment'
    _description = 'Security Post Assignment'
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    post_site_id = fields.Many2one('security.post.site', string='Post Site', required=True)
    employee_id = fields.Many2one('security.employee', string='Employee', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    start_time = fields.Float(string='Start Time', required=True)
    end_time = fields.Float(string='End Time', required=True)
    duration = fields.Float(string='Duration (Hours)', compute='_compute_duration', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    notes = fields.Text(string='Notes')
    
    # Related fields
    client_id = fields.Many2one(related='post_site_id.client_id', string='Client', store=True)
    premise_id = fields.Many2one(related='post_site_id.premise_id', string='Premise', store=True)
    location_id = fields.Many2one(related='post_site_id.location_id', string='Location', store=True)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('security.post.assignment') or _('New')
        return super(SecurityPostAssignment, self).create(vals_list)
    
    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for assignment in self:
            if assignment.start_time and assignment.end_time:
                if assignment.end_time >= assignment.start_time:
                    assignment.duration = assignment.end_time - assignment.start_time
                else:
                    # Handle overnight shifts
                    assignment.duration = (24 - assignment.start_time) + assignment.end_time
            else:
                assignment.duration = 0.0
    
    def action_assign(self):
        self.write({'state': 'assigned'})
    
    def action_start(self):
        self.write({
            'state': 'in_progress',
            'start_time': float(datetime.now().hour) + float(datetime.now().minute) / 60
        })
    
    def action_complete(self):
        self.write({
            'state': 'completed',
            'end_time': float(datetime.now().hour) + float(datetime.now().minute) / 60
        })
    
    def action_cancel(self):
        self.write({'state': 'cancelled'})
    
    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
