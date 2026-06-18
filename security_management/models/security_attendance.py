from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class SecurityAttendance(models.Model):
    _name = 'security.attendance'
    _description = 'Security Attendance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Reference', readonly=True, copy=False,
                      default=lambda self: _('New'))
    shift_assignment_id = fields.Many2one('security.shift.assignment', string='Shift Assignment', 
                                         required=True, ondelete='cascade')
    security_employee_id = fields.Many2one(related='shift_assignment_id.security_employee_id', string='Employee', store=True)
    shift_id = fields.Many2one(related='shift_assignment_id.shift_id', string='Shift', store=True)
    date = fields.Date(related='shift_assignment_id.date', string='Date', store=True)
    client_id = fields.Many2one(related='shift_assignment_id.client_id', string='Client', store=True)
    
    check_in = fields.Datetime(string='Check In', tracking=True)
    check_out = fields.Datetime(string='Check Out', tracking=True)
    
    # Duration in hours
    worked_hours = fields.Float(string='Worked Hours', compute='_compute_worked_hours', store=True)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('early_exit', 'Early Exit')
    ], string='Status', default='draft', tracking=True)
    
    timeoff_ids = fields.One2many('security.timeoff', 'attendance_id', string='Time Offs')
    notes = fields.Text(string='Notes')
    
    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        for record in self:
            if record.check_in and record.check_out:
                delta = record.check_out - record.check_in
                record.worked_hours = delta.total_seconds() / 3600.0
            else:
                record.worked_hours = 0.0
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('security.attendance') or _('New')
        return super(SecurityAttendance, self).create(vals_list)
    
    def action_check_in(self):
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError(_('Cannot check in. Attendance is not in draft state.'))
        self.write({
            'check_in': fields.Datetime.now(),
            'state': 'checked_in'
        })
    
    def action_check_out(self):
        self.ensure_one()
        if self.state != 'checked_in':
            raise ValidationError(_('Cannot check out. Employee has not checked in.'))
        self.write({
            'check_out': fields.Datetime.now(),
            'state': 'checked_out'
        })
    
    def action_mark_absent(self):
        self.ensure_one()
        self.write({'state': 'absent'})
    
    @api.constrains('check_in', 'check_out')
    def _check_validity_check_in_check_out(self):
        for attendance in self:
            if attendance.check_in and attendance.check_out:
                if attendance.check_out < attendance.check_in:
                    raise ValidationError(_('Check out time cannot be earlier than check in time.'))


class SecurityTimeoff(models.Model):
    _name = 'security.timeoff'
    _description = 'Security Time Off'
    
    name = fields.Char(string='Description', required=True)
    attendance_id = fields.Many2one('security.attendance', string='Attendance', required=True, ondelete='cascade')
    security_employee_id = fields.Many2one(related='attendance_id.security_employee_id', string='Employee', store=True)
    client_id = fields.Many2one(related='attendance_id.client_id', string='Client', store=True)
    
    date = fields.Date(string='Date', required=True)
    start_time = fields.Float(string='Start Time')
    end_time = fields.Float(string='End Time')
    duration = fields.Float(string='Duration (Hours)', compute='_compute_duration', store=True)
    
    reason = fields.Selection([
        ('break', 'Break'),
        ('lunch', 'Lunch'),
        ('personal', 'Personal'),
        ('medical', 'Medical'),
        ('other', 'Other')
    ], string='Reason', required=True)
    notes = fields.Text(string='Notes')
    
    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for record in self:
            if record.start_time is not False and record.end_time is not False:
                # Convert datetime to float if needed
                if isinstance(record.start_time, datetime):
                    start = float(record.start_time.hour + record.start_time.minute / 60.0)
                else:
                    start = float(record.start_time)
                    
                if isinstance(record.end_time, datetime):
                    end = float(record.end_time.hour + record.end_time.minute / 60.0)
                else:
                    end = float(record.end_time)
                    
                if end >= start:
                    record.duration = end - start
                else:
                    # Handle overnight timeoffs
                    record.duration = (24.0 - start) + end
            else:
                record.duration = 0.0
