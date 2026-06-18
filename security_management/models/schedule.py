# models/schedule.py
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, time
import pytz

_logger = logging.getLogger(__name__)

class SecurityShift(models.Model):
    _name = 'security.shift'
    _description = 'Security Shift'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Shift Name', required=True)
    code = fields.Char(string='Shift Code', required=True)
    shift_type_id = fields.Many2one('security.shift.type', string='Shift Type')
    sequence = fields.Integer(string='Sequence', default=10)
    start_time = fields.Float(string='Start Time', required=True)
    end_time = fields.Float(string='End Time', required=True)
    color = fields.Integer(string='Color')
    schedule_id = fields.Many2one('security.schedule', string='Schedule', ondelete='cascade', required=True)
    active = fields.Boolean(default=True)
    # Duration in hours
    duration = fields.Float(string='Duration (Hours)', compute='_compute_duration', store=True)
    # Computed fields
    assigned_count = fields.Integer(compute='_compute_assigned_count', string='Assigned Guards')
    # state
    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True, compute='_compute_state', store=True)
    assignment_ids = fields.One2many('security.shift.assignment', 'shift_id', string='Assignments')
    min_guards = fields.Integer(string='Minimum Guards', default=1)
    max_guards = fields.Integer(string='Maximum Guards', default=1)
    notes = fields.Text(string='Notes')

    @api.depends('state')
    def _compute_state(self):
        for shift in self:
            if not shift.start_time or not shift.end_time:
                shift.state = 'draft'
                continue

            if shift.start_time > shift.end_time:
                shift.state = 'draft'
            elif shift.start_time <= datetime.now().time() <= shift.end_time:
                shift.state = 'in_progress'
            elif shift.end_time < datetime.now().time():
                shift.state = 'completed'
            else:
                shift.state = 'draft'

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for shift in self:
            if shift.end_time >= shift.start_time:
                shift.duration = shift.end_time - shift.start_time
            else:
                # Handle overnight shifts
                shift.duration = (24.0 - shift.start_time) + shift.end_time

    @api.depends('assignment_ids')
    def _compute_assigned_count(self):
        for shift in self:
            shift.assigned_count = len(shift.assignment_ids)

    @api.constrains('start_time', 'end_time')
    def _check_times(self):
        for shift in self:
            if shift.start_time < 0 or shift.start_time >= 24 or shift.end_time < 0 or shift.end_time >= 24:
                raise ValidationError(_("Shift times must be between 0 and 24"))

            if shift.start_time == shift.end_time:
                raise ValidationError(_("Shift start and end times cannot be the same"))

    def action_view_assignments(self):
        self.ensure_one()
        return {
            'name': _('Guard Assignments'),
            'view_mode': 'tree,form',
            'res_model': 'security.shift.assignment',
            'domain': [('shift_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_shift_id': self.id},
        }


class SecuritySchedule(models.Model):
    _name = 'security.schedule'
    _description = 'Security Schedule'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Schedule Reference', required=True, copy=False, readonly=True,
                     default=lambda self: _('New'))
    team_id = fields.Many2one('security.team', string='Team', required=True, tracking=True)
    client_id = fields.Many2one('security.client', string='Client', required=True, tracking=True)
    premise_id = fields.Many2one('security.premise', string='Premise', tracking=True)
    created_by = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user, readonly=True)
    start_date = fields.Date(string='Start Date', required=True, tracking=True)
    end_date = fields.Date(string='End Date', required=True, tracking=True)
    duration_days = fields.Integer(string='Duration (Days)', compute='_compute_duration_days', store=True)
    is_recurring = fields.Boolean(string='Recurring Schedule', default=False)
    recurrence_interval = fields.Integer(string='Repeat Every', default=1)
    recurrence_type = fields.Selection([
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months'),
        ('year', 'Years')
    ], string='Recurrence Unit', default='week')
    active = fields.Boolean(default=True)

    # Relations
    shift_assignment_ids = fields.One2many('security.shift.assignment', 'schedule_id', string='Shift Assignments')
    assignment_ids = fields.One2many('security.shift.assignment', 'schedule_id', string='Assignments')
    shift_ids = fields.One2many('security.shift', 'schedule_id', string='Shifts')

    # Computed fields
    assignment_count = fields.Integer(compute='_compute_assignment_count', string='Assignments')
    shift_count = fields.Integer(compute='_compute_shift_count', string='Shifts')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True, compute='_compute_state', store=True)
    notes = fields.Text(string='Notes')

    @api.depends('shift_assignment_ids')
    def _compute_assignment_count(self):
        for schedule in self:
            schedule.assignment_count = len(schedule.shift_assignment_ids)

    @api.depends('shift_ids')
    def _compute_shift_count(self):
        for schedule in self:
            schedule.shift_count = len(schedule.shift_ids)

    @api.depends('start_date', 'end_date')
    def _compute_state(self):
        today = fields.Date.today()
        for schedule in self:
            if not schedule.start_date or not schedule.end_date:
                schedule.state = 'draft'
                continue

            if schedule.start_date > today:
                schedule.state = 'confirmed'
            elif schedule.start_date <= today <= schedule.end_date:
                schedule.state = 'in_progress'
            elif schedule.end_date < today:
                schedule.state = 'completed'

    @api.depends('start_date', 'end_date')
    def _compute_duration_days(self):
        for schedule in self:
            if schedule.start_date and schedule.end_date:
                delta = schedule.end_date - schedule.start_date
                schedule.duration_days = delta.days + 1
            else:
                schedule.duration_days = 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('security.schedule') or _('New')
        return super().create(vals_list)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for schedule in self:
            if schedule.start_date and schedule.end_date and schedule.start_date > schedule.end_date:
                raise ValidationError(_("Schedule end date must be after start date"))

    def action_view_assignments(self):
        self.ensure_one()
        return {
            'name': _('Shift Assignments'),
            'view_mode': 'tree,form,calendar',
            'res_model': 'security.shift.assignment',
            'domain': [('schedule_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_schedule_id': self.id},
        }

    def action_view_shifts(self):
        self.ensure_one()
        return {
            'name': _('Shifts'),
            'view_mode': 'tree,form',
            'res_model': 'security.shift',
            'domain': [('schedule_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_schedule_id': self.id},
        }

    def action_confirm(self):
        """Confirm the schedule"""
        self.ensure_one()
        if not self.shift_assignment_ids:
            raise UserError(_("Cannot confirm a schedule without shift assignments"))

        self.write({
            'state': 'confirmed',
        })
        return True

    def action_cancel(self):
        """Cancel the schedule"""
        self.ensure_one()
        if self.state == 'completed':
            raise UserError(_("Cannot cancel a completed schedule"))

        self.write({
            'state': 'cancelled',
        })
        return True

    def action_start(self):
        """Start the schedule"""
        self.ensure_one()
        if self.state != 'confirmed':
            raise UserError(_("Only confirmed schedules can be started"))

        self.write({
            'state': 'in_progress',
        })
        return True

    def action_complete(self):
        """Complete the schedule"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_("Only in-progress schedules can be completed"))

        self.write({
            'state': 'completed',
        })
        return True

    def action_reset(self):
        """Reset the schedule to draft"""
        self.ensure_one()
        if self.state != 'cancelled':
            raise UserError(_("Only cancelled schedules can be reset to draft"))

        self.write({
            'state': 'draft',
        })
        return True

    def action_generate_shifts(self):
        """Open wizard to generate shifts"""
        self.ensure_one()
        return {
            'name': _('Generate Shifts'),
            'view_mode': 'form',
            'res_model': 'security.generate.shifts.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_schedule_id': self.id,
                'default_start_date': self.start_date,
                'default_end_date': self.end_date,
            },
        }


class SecurityShiftAssignment(models.Model):
    _name = 'security.shift.assignment'
    _description = 'Shift Assignment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', readonly=True, copy=False,
                     default=lambda self: _('New'))
    schedule_id = fields.Many2one('security.schedule', string='Schedule', ondelete='cascade', required=True,
                                  default=lambda self: self._get_default_schedule())
    security_employee_id = fields.Many2one('security.employee', string='Employee', store=True, tracking=True,
                                           default=lambda self: self.env.context.get('default_security_employee_id'), compute="_get_security_employee_id")
    shift_id = fields.Many2one('security.shift', string='Shift', required=True, tracking=True, domain="[('schedule_id', '!=', False)]")
    date = fields.Date(string='Date', required=True, tracking=True)

    # Computed and related fields
    client_id = fields.Many2one(related='schedule_id.client_id', string='Client', store=True)
    
    # Datetime fields
    start_datetime = fields.Datetime(string='Start Time', store=True, compute='_update_datetime_fields')
    end_datetime = fields.Datetime(string='End Time', store=True, compute='_update_datetime_fields')
    date_from = fields.Date('Date From')
    # Status fields
    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('missed', 'Missed'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='scheduled', tracking=True)

    attendance_id = fields.Many2one('security.attendance', string='Attendance Record')
    # Related fields for attendance data
    attendance_check_in = fields.Datetime(related='attendance_id.check_in', string='Check In Time', readonly=True)
    attendance_check_out = fields.Datetime(related='attendance_id.check_out', string='Check Out Time', readonly=True)
    attendance_worked_hours = fields.Float(related='attendance_id.worked_hours', string='Worked Hours', readonly=True)
    attendance_timeoff_ids = fields.One2many(related='attendance_id.timeoff_ids', string='Time Offs', readonly=True)
    notes = fields.Text(string='Notes')
    color = fields.Integer(related='shift_id.color', string='Color')
    guard_id = fields.Many2one('security.guard', string='Guard')

    _sql_constraints = [
        ('employee_shift_date_uniq', 'unique(security_employee_id, date, shift_id)',
         'Employee cannot be assigned to the same shift twice on the same day!')
    ]
    
    def _get_default_schedule(self):
        """Get the default schedule from context or related shift"""
        # If creating from a shift, get the schedule from the shift
        if 'params' in self.env.context and self.env.context.get('params').get('model') == 'security.shift':
            shift_id = self.env.context.get('params').get('id')
            if shift_id:
                shift = self.env['security.shift'].browse(shift_id)
                if shift and shift.schedule_id:
                    return shift.schedule_id.id
        else:
            return False
                    
        return False
    
    @api.model
    def create(self, vals):
        """Override create to ensure schedule_id is set"""
        # If shift_id is provided but schedule_id is not, get schedule from shift
        if 'shift_id' in vals and not vals.get('schedule_id'):
            shift = self.env['security.shift'].browse(vals['shift_id'])
            if shift and shift.schedule_id:
                vals['schedule_id'] = shift.schedule_id.id
                
        return super(SecurityShiftAssignment, self).create(vals)
    
    @api.depends('guard_id')
    def _get_security_employee_id(self):
        for record in self:
            if record.guard_id and record.guard_id.security_employee_id:
                record.security_employee_id = record.guard_id.security_employee_id
            else:
                record.security_employee_id = False
            
    @api.onchange('guard_id')
    def _onchange_guard_id(self):
        for record in self:
            if record.guard_id and record.guard_id.security_employee_id and record.guard_id.security_employee_id.employee_id:
                record.security_employee_id.employee_id = record.guard_id.security_employee_id.employee_id.id
            else:
                record.security_employee_id.employee_id = False
                
    @api.onchange('shift_id')
    def _onchange_shift_id(self):
        """When shift changes, update the schedule_id from the shift and set default times"""
        for record in self:
            if record.shift_id and record.shift_id.schedule_id:
                record.schedule_id = record.shift_id.schedule_id
            # Update datetime fields
            record._update_datetime_fields()
    
    @api.depends('date', 'shift_id')       
    def _update_datetime_fields(self):
        """Helper method to update datetime fields based on date and shift times"""
        self.ensure_one()
        
        if not self.date or not self.shift_id:
            self.start_datetime = False
            self.end_datetime = False
            return
            
        # Always use the shift's time values
        start_time = self.shift_id.start_time
        end_time = self.shift_id.end_time
        
        # Convert float time to hours and minutes
        start_hours = int(start_time)
        start_minutes = int((start_time - start_hours) * 60)
        
        end_hours = int(end_time)
        end_minutes = int((end_time - end_hours) * 60)
        
        # Create time objects
        start_time_obj = time(start_hours, start_minutes)
        end_time_obj = time(end_hours, end_minutes)
        
        # Create naive datetime objects first
        start_datetime_naive = datetime.combine(self.date, start_time_obj)
        
        # Handle overnight shifts
        is_overnight = end_time < start_time
        
        if is_overnight:
            end_datetime_naive = datetime.combine(self.date + timedelta(days=1), end_time_obj)
        else:
            end_datetime_naive = datetime.combine(self.date, end_time_obj)
        
        # Convert to UTC (Odoo stores datetimes in UTC)
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')
        
        # Localize the naive datetime to user timezone, then convert to UTC
        start_datetime_local = user_tz.localize(start_datetime_naive)
        end_datetime_local = user_tz.localize(end_datetime_naive)
        
        self.start_datetime = start_datetime_local.astimezone(pytz.UTC).replace(tzinfo=None)
        self.end_datetime = end_datetime_local.astimezone(pytz.UTC).replace(tzinfo=None)
        
        print("########## Debug Info ##########")
        print(f"Shift start_time (float): {start_time}")
        print(f"Shift end_time (float): {end_time}")
        print(f"Date: {self.date}")
        print(f"User timezone: {self.env.user.tz}")
        print(f"Start datetime (naive): {start_datetime_naive}")
        print(f"End datetime (naive): {end_datetime_naive}")
        print(f"Start datetime (UTC): {self.start_datetime}")
        print(f"End datetime (UTC): {self.end_datetime}")
        print("################################")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Set sequence number if not provided
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('security.shift.assignment') or _('New')
                
            # If shift_id and date are provided but start/end datetimes are not set, calculate them
            if vals.get('shift_id') and vals.get('date') and not (vals.get('start_datetime') and vals.get('end_datetime')):
                shift = self.env['security.shift'].browse(vals.get('shift_id'))
                date = datetime.strptime(vals.get('date'), '%Y-%m-%d').date() if isinstance(vals.get('date'), str) else vals.get('date')
                
                # Calculate start datetime
                start_hours = int(shift.start_time)
                start_minutes = int((shift.start_time - start_hours) * 60)
                vals['start_datetime'] = datetime.combine(
                    date,
                    datetime.min.time()
                ) + timedelta(hours=start_hours, minutes=start_minutes)
                
                # Calculate end datetime
                end_hours = int(shift.end_time)
                end_minutes = int((shift.end_time - end_hours) * 60)
                
                # Handle overnight shifts
                if shift.end_time < shift.start_time:
                    vals['end_datetime'] = datetime.combine(
                        date + timedelta(days=1),
                        datetime.min.time()
                    ) + timedelta(hours=end_hours, minutes=end_minutes)
                else:
                    vals['end_datetime'] = datetime.combine(
                        date,
                        datetime.min.time()
                    ) + timedelta(hours=end_hours, minutes=end_minutes)
                    
        return super().create(vals_list)

    def action_check_in(self):
        """Check in the employee for the shift"""
        self.ensure_one()
        if self.state != 'scheduled':
            raise UserError(_("Only scheduled shifts can be checked in"))

        # Create attendance record
        attendance = self.env['security.attendance'].create({
            'shift_assignment_id': self.id,
            'check_in_time': fields.Datetime.now(),
        })

        self.write({
            'state': 'checked_in',
            'attendance_id': attendance.id,
        })
        return True

    def action_check_out(self):
        """Check out the employee from the shift"""
        self.ensure_one()
        if self.state != 'checked_in':
            raise UserError(_("Only checked in shifts can be checked out"))

        if not self.attendance_id:
            raise UserError(_("No attendance record found for this shift"))

        self.attendance_id.write({
            'check_out_time': fields.Datetime.now(),
        })

        self.write({
            'state': 'checked_out',
        })
        return True

    def action_mark_missed(self):
        """Mark the shift as missed"""
        self.ensure_one()
        if self.state in ['checked_in', 'checked_out']:
            raise UserError(_("Cannot mark a shift as missed if employee already checked in/out"))

        self.write({
            'state': 'missed',
        })
        return True

    def action_cancel(self):
        """Cancel the shift assignment"""
        self.ensure_one()
        if self.state in ['checked_in', 'checked_out']:
            raise UserError(_("Cannot cancel a shift if employee already checked in/out"))

        self.write({
            'state': 'cancelled',
        })
        return True

    def action_timeoff(self):
        """Open wizard to record time off"""
        self.ensure_one()
        if self.state != 'checked_in':
            raise UserError(_("Employee must be checked in to record time off"))

        if not self.attendance_id:
            raise UserError(_("No attendance record found for this shift"))

        return {
            'name': _('Record Time Off'),
            'view_mode': 'form',
            'res_model': 'security.timeoff.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_attendance_id': self.attendance_id.id,
            },
        }


class SecurityAssignment(models.Model):
    _name = 'security.assignment'
    _description = 'Security Assignment'
    _inherits = {'security.shift.assignment': 'shift_assignment_id'}

    shift_assignment_id = fields.Many2one('security.shift.assignment', string='Shift Assignment',
                                        required=True, ondelete='cascade', auto_join=True)

    # Add state field to support the workflow
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    # Add fields for check-in and check-out
    check_in = fields.Datetime(string='Check In')
    check_out = fields.Datetime(string='Check Out')

    # Add field for guard
    guard_id = fields.Many2one('security.guard', string='Guard', required=True)
    active = fields.Boolean(default=True)

    @api.model
    def create(self, vals):
        """Override create method to properly handle shift assignment creation"""
        # If shift_assignment_id is already provided, use it
        if vals.get('shift_assignment_id'):
            return super(SecurityAssignment, self).create(vals)
            
        # Make sure employee_id is set from guard_id
        if vals.get('guard_id'):
            guard = self.env['security.guard'].browse(vals['guard_id'])
            if guard and guard.security_employee_id and guard.security_employee_id.employee_id:
                vals['security_employee_id'] = guard.security_employee_id.employee_id.id
                
        # Otherwise, create a new shift_assignment first
        shift_assignment_vals = {}
        
        # Ensure required fields are included
        required_fields = ['date', 'shift_id', 'schedule_id', 'employee_id']
        for field in required_fields:
            if field not in vals and field not in shift_assignment_vals:
                # Try to derive the value
                if field == 'schedule_id' and vals.get('shift_id'):
                    shift = self.env['security.shift'].browse(vals.get('shift_id'))
                    if shift and shift.schedule_id:
                        shift_assignment_vals['schedule_id'] = shift.schedule_id.id
                elif field == 'security_employee_id' and vals.get('guard_id'):
                    guard = self.env['security.guard'].browse(vals['guard_id'])
                    if guard and guard.employee_id:
                        shift_assignment_vals['security_employee_id'] = guard.employee_id.id
                        
        # Copy all fields that are common between security.assignment and security.shift.assignment
        for field in self.env['security.shift.assignment']._fields:
            if field in vals and field != 'id' and field != 'state':
                shift_assignment_vals[field] = vals[field]
        
        # Make sure state is set correctly - 'draft' is not valid for shift_assignment
        # Set it to 'scheduled' which is the default for shift_assignment
        shift_assignment_vals['state'] = 'scheduled'
        
        # Make sure schedule_id is set (highest priority)
        if not shift_assignment_vals.get('schedule_id'):
            # Try to get it from shift_id (this is the most reliable source)
            if shift_assignment_vals.get('shift_id'):
                shift = self.env['security.shift'].browse(shift_assignment_vals.get('shift_id'))
                if shift and shift.schedule_id:
                    shift_assignment_vals['schedule_id'] = shift.schedule_id.id
            
            # If still not set, try context (e.g., from action defaults)
            if not shift_assignment_vals.get('schedule_id') and self._context.get('default_schedule_id'):
                shift_assignment_vals['schedule_id'] = self._context.get('default_schedule_id')
                
            # If still not set, get the latest active schedule
            if not shift_assignment_vals.get('schedule_id'):
                latest_schedule = self.env['security.schedule'].search(
                    [('state', 'in', ['confirmed', 'in_progress'])], 
                    limit=1, order='id desc'
                )
                if latest_schedule:
                    shift_assignment_vals['schedule_id'] = latest_schedule.id
        
        # Double check - Ensure required fields are set before creating the shift assignment
        for field in ['date', 'shift_id', 'schedule_id']:
            if not shift_assignment_vals.get(field):
                raise UserError(_(f'Cannot create assignment: {field} is required.'))
        
        # Set default start and end datetime based on shift times if available
        if shift_assignment_vals.get('shift_id') and shift_assignment_vals.get('date'):
            shift = self.env['security.shift'].browse(shift_assignment_vals.get('shift_id'))
            date_val = shift_assignment_vals.get('date')
            
            # Ensure date is a proper date object
            if isinstance(date_val, str):
                try:
                    date_val = datetime.strptime(date_val, '%Y-%m-%d').date()
                except ValueError:
                    # Skip this part if date is invalid
                    _logger.warning(f"Invalid date format encountered: {date_val}")
                    date_val = None
                    
            # Only proceed if we have a valid date
            if date_val and (hasattr(date_val, 'day') and hasattr(date_val, 'month') and hasattr(date_val, 'year')):
                # Convert to date if it's a datetime
                if hasattr(date_val, 'hour') and hasattr(date_val, 'minute'):
                    # It's likely a datetime object if it has hour and minute attributes
                    date_val = date_val.date()
                    
                # Calculate start datetime
                start_hours = int(shift.start_time)
                start_minutes = int((shift.start_time - start_hours) * 60)
                shift_assignment_vals['start_datetime'] = datetime.combine(
                    date_val,
                    datetime.min.time()
                ) + timedelta(hours=start_hours, minutes=start_minutes)
                
                # Calculate end datetime
                end_hours = int(shift.end_time)
                end_minutes = int((shift.end_time - end_hours) * 60)
                
                # Handle overnight shifts
                if shift.end_time < shift.start_time:
                    shift_assignment_vals['end_datetime'] = datetime.combine(
                        date_val + timedelta(days=1),
                        datetime.min.time()
                    ) + timedelta(hours=end_hours, minutes=end_minutes)
                else:
                    shift_assignment_vals['end_datetime'] = datetime.combine(
                        date_val,
                        datetime.min.time()
                    ) + timedelta(hours=end_hours, minutes=end_minutes)
        
        # Create the shift assignment
        shift_assignment = self.env['security.shift.assignment'].sudo().create(shift_assignment_vals)
        # Create the security.assignment with link to the shift assignment
        vals['shift_assignment_id'] = shift_assignment.id
        return super(SecurityAssignment, self).create(vals)

    def action_confirm(self):
        """Confirm the assignment"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Only draft assignments can be confirmed"))

            record.write({
                'state': 'confirmed',
            })
        return True

    def action_start(self):
        """Start the assignment"""
        for record in self:
            if record.state != 'confirmed':
                raise UserError(_("Only confirmed assignments can be started"))

            record.write({
                'state': 'in_progress',
                'check_in': fields.Datetime.now(),
            })
        return True

    def action_complete(self):
        """Complete the assignment"""
        for record in self:
            if record.state != 'in_progress':
                raise UserError(_("Only in-progress assignments can be completed"))

            record.write({
                'state': 'completed',
                'check_out': fields.Datetime.now(),
            })
        return True

    def action_cancel(self):
        """Cancel the assignment"""
        for record in self:
            if record.state in ('completed', 'cancelled'):
                raise UserError(_("Completed or cancelled assignments cannot be cancelled"))

            record.write({
                'state': 'cancelled',
            })
        return True

                

class SecurityAttendance(models.Model):
    _name = 'security.attendance'
    _description = 'Security Attendance'
    _order = 'check_in_time desc'

    shift_assignment_id = fields.Many2one('security.shift.assignment', string='Shift Assignment', required=True)
    security_employee_id = fields.Many2one(related='shift_assignment_id.security_employee_id', string='Employee', store=True)
    shift_id = fields.Many2one(related='shift_assignment_id.shift_id', string='Shift', store=True)
    date = fields.Date(related='shift_assignment_id.date', string='Date', store=True)
    client_id = fields.Many2one(related='shift_assignment_id.client_id', string='Client', store=True)

    check_in_time = fields.Datetime(string='Check In', required=True)
    check_out_time = fields.Datetime(string='Check Out')

    timeoff_ids = fields.One2many('security.timeoff', 'attendance_id', string='Time Offs')

    # Computed fields
    worked_hours = fields.Float(compute='_compute_worked_hours', string='Worked Hours', store=True)
    timeoff_hours = fields.Float(compute='_compute_timeoff_hours', string='Time Off Hours', store=True)
    effective_hours = fields.Float(compute='_compute_effective_hours', string='Effective Hours', store=True)

    @api.depends('check_in_time', 'check_out_time')
    def _compute_worked_hours(self):
        for attendance in self:
            if attendance.check_in_time and attendance.check_out_time:
                delta = attendance.check_out_time - attendance.check_in_time
                attendance.worked_hours = delta.total_seconds() / 3600
            else:
                attendance.worked_hours = 0

    @api.depends('timeoff_ids', 'timeoff_ids.duration')
    def _compute_timeoff_hours(self):
        for attendance in self:
            attendance.timeoff_hours = sum(attendance.timeoff_ids.mapped('duration'))

    @api.depends('worked_hours', 'timeoff_hours')
    def _compute_effective_hours(self):
        for attendance in self:
            attendance.effective_hours = attendance.worked_hours - attendance.timeoff_hours


class SecurityTimeoff(models.Model):
    _name = 'security.timeoff'
    _description = 'Security Time Off'

    attendance_id = fields.Many2one('security.attendance', string='Attendance', required=True, ondelete='cascade')
    security_employee_id = fields.Many2one(related='attendance_id.security_employee_id', string='Employee', store=True)
    client_id = fields.Many2one(related='attendance_id.client_id', string='Client', store=True)

    start_time = fields.Datetime(string='Start Time', required=True)
    end_time = fields.Datetime(string='End Time', required=True)
    duration = fields.Float(compute='_compute_duration', string='Duration (Hours)', store=True)
    reason = fields.Text(string='Reason', required=True)

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for timeoff in self:
            if timeoff.start_time and timeoff.end_time:
                delta = timeoff.end_time - timeoff.start_time
                timeoff.duration = delta.total_seconds() / 3600
            else:
                timeoff.duration = 0

    @api.constrains('start_time', 'end_time')
    def _check_times(self):
        for timeoff in self:
            if timeoff.start_time >= timeoff.end_time:
                raise ValidationError(_("Time off end time must be after start time"))

            if timeoff.attendance_id.check_in_time and timeoff.start_time < timeoff.attendance_id.check_in_time:
                raise ValidationError(_("Time off cannot start before check in time"))

            if timeoff.attendance_id.check_out_time and timeoff.end_time > timeoff.attendance_id.check_out_time:
                raise ValidationError(_("Time off cannot end after check out time"))
