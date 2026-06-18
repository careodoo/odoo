from odoo import api, fields, models, _
from datetime import datetime


class SecurityGuard(models.Model):
    _name = 'security.guard'
    _description = 'Security Guard'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Name', required=True, tracking=True)
    security_employee_id = fields.Many2one('security.employee', string='Employee Record', tracking=True)
    user_id = fields.Many2one('res.users', string='Related User', tracking=True)
    patrol_log_ids = fields.One2many('security.patrol.log', 'guard_id', string='Patrol Logs')
    # Personal Information
    identification_number = fields.Char(string='ID Number', tracking=True)
    phone = fields.Char(string='Phone', tracking=True)
    email = fields.Char(string='Email', tracking=True)
    address = fields.Text(string='Address')

    @api.onchange('security_employee_id')
    def _onchange_employee_id(self):
        if self.security_employee_id:
            # Copy data from security employee to guard
            self.name = self.security_employee_id.name
            self.phone = self.security_employee_id.phone
            self.email = self.security_employee_id.email
            self.badge_number = self.security_employee_id.badge_number
            self.license_number = self.security_employee_id.license_number
            self.license_expiry = self.security_employee_id.license_expiry
            self.security_employee_id = self.security_employee_id.id
            self.security_employee_role_id = self.security_employee_id.role_id.id
            self.security_employee_team_ids = [(6, 0, self.security_employee_id.team_ids.ids)] if self.security_employee_id.team_ids else False

            # Copy skills
            if self.security_employee_id.skill_ids:
                self.skill_ids = [(6, 0, self.security_employee_id.skill_ids.ids)]

            # Set availability based on employee
            self.is_available = self.security_employee_id.is_available

            # Copy image if available
            if hasattr(self.security_employee_id, 'image_1920') and self.security_employee_id.image_1920:
                self.image_1920 = self.security_employee_id.image_1920

            # We need to handle certifications in create method since they are one2many fields

            # Status and Assignment
            self.status = 'active'

    post_site = fields.Many2one('security.post.site', string='Assigned Post', tracking=True)
    shift_id = fields.Many2one('security.shift', string='Current Shift', tracking=True)

    # Skills and Certifications
    skill_ids = fields.Many2many('security.skill', string='Skills')
    certification_ids = fields.One2many('security.certification', 'guard_id', string='Certifications')

    # Equipment
    equipment_ids = fields.Many2many('security.equipment', string='Assigned Equipment')

    # Image
    image_1920 = fields.Image("Image", max_width=1920, max_height=1920)
    image_128 = fields.Image("Image (small)", related="image_1920", max_width=128, max_height=128, store=True)

    # Tracking
    last_update = fields.Datetime(string='Last Update', default=fields.Datetime.now)
    last_location_id = fields.Many2one('security.location', string='Last Known Location')
    last_check_in = fields.Datetime(string='Last Check-in')
    
    # Tasks assigned to this guard
    task_ids = fields.One2many('security.task', 'assigned_to', string='Assigned Tasks')

    # Mobile app tracking fields
    battery_level = fields.Integer(string='Battery Level', default=100)
    speed = fields.Float(string='Speed (km/h)', default=0.0)
    location = fields.Char(string='Location Description')
    latitude = fields.Float(string='Latitude', digits=(16, 8))
    longitude = fields.Float(string='Longitude', digits=(16, 8))

    # Statistics
    completed_shifts_count = fields.Integer(string='Completed Shifts', compute='_compute_statistics')
    completed_tasks_count = fields.Integer(string='Completed Tasks', compute='_compute_statistics')
    incident_reports_count = fields.Integer(string='Incident Reports', compute='_compute_statistics')
    patrol_count = fields.Integer(string='Patrol Count', compute='_compute_patrol_count')
    task_count = fields.Integer(string='Task Count', compute='_compute_task_count')
    schedule_count = fields.Integer(string='Schedule Count', compute='_compute_schedule_count')
    image = fields.Binary(string='Image', attachment=True)
    security_employee_id = fields.Many2one('security.employee', string='Security Employee', ondelete='cascade')
    security_employee_role_id = fields.Many2one('security.role', string='Role', store=True)
    security_employee_team_ids = fields.Many2many('security.team', string='Team', store=True)
    active = fields.Boolean(string='Active', default=True)
    badge_number = fields.Char(string='Badge Number')
    license_number = fields.Char(string='License Number')
    license_expiry = fields.Date(string='License Expiry')
    is_available = fields.Boolean(string='Is Available', default=True)
    years_experience = fields.Float(string='Years of Experience')
    join_date = fields.Date(related='security_employee_id.employee_id.contract_id.date_start', store=True)
    notes = fields.Text(string='Notes')
    # Schedule assignments
    schedule_assignment_ids = fields.One2many('security.shift.assignment', 'guard_id', string='Schedule Assignments')

    status = fields.Selection([
        ('active', 'Active'),
        ('on_leave', 'On Leave'),
        ('inactive', 'Inactive')
    ], string='Status', default='active', tracking=True)

    @api.depends('security_employee_id')
    def _compute_statistics(self):
        for guard in self:
            if guard.security_employee_id:
                # These would be computed based on related employee record
                guard.completed_shifts_count = self.env['security.shift.assignment'].search_count([
                    ('security_employee_id', '=', guard.security_employee_id.id),
                    ('state', '=', 'completed')
                ]) if 'security.shift.assignment' in self.env else 0

                guard.completed_tasks_count = self.env['security.task.assignment'].search_count([
                    ('security_employee_id', '=', guard.security_employee_id.id),
                    ('state', '=', 'completed')
                ]) if 'security.task.assignment' in self.env else 0

                guard.incident_reports_count = self.env['security.incidence.report'].search_count([
                    ('reported_by_id', '=', guard.security_employee_id.id)
                ]) if 'security.incidence.report' in self.env else 0
            else:
                guard.completed_shifts_count = 0
                guard.completed_tasks_count = 0
                guard.incident_reports_count = 0

    @api.depends('security_employee_id')
    def _compute_patrol_count(self):
        for guard in self:
            guard.patrol_count = self.env['security.patrol.log'].search_count([
                ('guard_id', '=', guard.id)
            ]) if 'security.patrol.log' in self.env else 0

    @api.depends('security_employee_id')
    def _compute_task_count(self):
        for guard in self:
            guard.task_count = self.env['security.task'].search_count([
                ('assigned_to', '=', guard.id)
            ]) if 'security.task' in self.env else 0

    @api.depends('security_employee_id')
    def _compute_schedule_count(self):
        for guard in self:
            if guard.security_employee_id:
                # Look for schedules through shift assignments
                guard.schedule_count = self.env['security.shift.assignment'].search_count([
                    ('security_employee_id', '=', guard.security_employee_id.id)
                ]) if 'security.shift.assignment' in self.env else 0
            else:
                guard.schedule_count = 0

    def update_location(self, location_id):
        """Update the guard's last known location"""
        self.write({
            'last_location_id': location_id,
            'last_update': fields.Datetime.now()
        })

    def check_in(self):
        """Record a check-in for the guard"""
        self.write({
            'last_check_in': fields.Datetime.now(),
            'last_update': fields.Datetime.now()
        })

        # Create a check-in record if the model exists
        if 'security.checkin' in self.env and self.security_employee_id:
            self.env['security.checkin'].create({
                'employee_id': self.security_employee_id.id,
                'date': fields.Date.today(),
                'time': float(datetime.now().hour) + float(datetime.now().minute) / 60,
                'location_id': self.last_location_id.id if self.last_location_id else False,
                'state': 'confirmed'
            })

        return True

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to copy certifications from employee"""
        records = super().create(vals_list)

        for record in records:
            if record.security_employee_id and record.security_employee_id.certification_ids:
                # Copy certifications from employee to guard
                for cert in record.security_employee_id.certification_ids:
                    self.env['security.certification'].create({
                        'name': cert.name,
                        'certification_number': cert.certification_number,
                        'issue_date': cert.issue_date,
                        'expiry_date': cert.expiry_date,
                        'issuing_authority': cert.issuing_authority,
                        'guard_id': record.id,
                    })

        return records

    def action_view_patrols(self):
        """View patrol logs for this guard"""
        self.ensure_one()
        return {
            'name': _('Patrol Logs'),
            'view_mode': 'tree,form',
            'res_model': 'security.patrol.log',
            'domain': [('guard_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_guard_id': self.id},
        }

    def action_view_tasks(self):
        """View tasks assigned to this guard"""
        self.ensure_one()
        return {
            'name': _('Tasks'),
            'view_mode': 'tree,form',
            'res_model': 'security.task',
            'domain': [('assigned_to', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_assigned_to': self.id},
        }

    def action_view_schedules(self):
        """View schedules for this guard"""
        self.ensure_one()
        return {
            'name': _('Schedules'),
            'view_mode': 'tree,form',
            'res_model': 'security.shift.assignment',
            'domain': [('security_employee_id', '=', self.security_employee_id.id)],
            'type': 'ir.actions.act_window',
        }
