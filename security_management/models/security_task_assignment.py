from odoo import api, fields, models, _
from datetime import datetime


class SecurityTaskAssignment(models.Model):
    _name = 'security.task.assignment'
    _description = 'Security Task Assignment'
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    task_id = fields.Many2one('security.task', string='Task', required=True, ondelete='cascade')
    employee_id = fields.Many2one('security.employee', string='Employee', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    start_time = fields.Float(string='Start Time')
    end_time = fields.Float(string='End Time')
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
    task_name = fields.Char(related='task_id.name', string='Task Name', store=True)
    location_id = fields.Many2one(related='task_id.location_id', string='Location', store=True)
    premise_id = fields.Many2one(related='task_id.premise_id', string='Premise', store=True)
    client_id = fields.Many2one(related='task_id.client_id', string='Client', store=True)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('security.task.assignment') or _('New')
        return super(SecurityTaskAssignment, self).create(vals_list)
    
    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for assignment in self:
            if assignment.start_time and assignment.end_time:
                if assignment.end_time >= assignment.start_time:
                    assignment.duration = assignment.end_time - assignment.start_time
                else:
                    # Handle overnight assignments
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
