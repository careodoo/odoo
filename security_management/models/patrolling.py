import logging
import json
from datetime import datetime, time, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import random
import string
import qrcode
import base64
from io import BytesIO

class SecurityPatrolPoint(models.Model):
    _name = 'security.patrol.point'
    _description = 'Patrol Point'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Point Name', required=True, tracking=True)
    code = fields.Char(string='Point Code', tracking=True, copy=False)
    barcode = fields.Char(string='Barcode', readonly=True, copy=False)
    qr_code = fields.Binary(string='QR Code', readonly=True, copy=False, attachment=True)
    qr_code_text = fields.Char(string='QR Code Text', readonly=True, copy=False)

    # Location hierarchy
    premise_id = fields.Many2one('security.premise', string='Premise', required=True, tracking=True)
    floor_id = fields.Many2one('security.floor', string='Floor', tracking=True,
                              domain="[('premise_id', '=', premise_id or False)]")
    unit_id = fields.Many2one('security.unit', string='Unit', tracking=True,
                             domain="[('floor_id', '=', floor_id or False)]")
    location_id = fields.Many2one('security.location', string='Location', tracking=True)

    # Additional information
    description = fields.Text(string='Description')
    point_type = fields.Selection([
        ('checkpoint', 'Checkpoint'),
        ('patrol', 'Patrol Point'),
        ('emergency', 'Emergency Point'),
        ('entrance', 'Entrance/Exit')
    ], string='Point Type', default='patrol', required=True, tracking=True)

    # Company field for multi-company support
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        groups='base.group_multi_company',
        help='Company this patrol point belongs to'
    )

    # Schedule for checkpoints
    check_interval = fields.Float(string='Check Interval (Hours)',
                                 help="How often this point should be checked (in hours)")
    last_check_time = fields.Datetime(string='Last Checked', readonly=True)
    next_check_time = fields.Datetime(string='Next Check Due', compute='_compute_next_check_time', store=True)

    # Related fields
    client_id = fields.Many2one(related='premise_id.client_id', string='Client', store=True)
    patrol_log_ids = fields.One2many('security.patrol.log', 'point_id', string='Patrol Logs')

    # Computed fields
    log_count = fields.Integer(compute='_compute_log_count', string='Log Count')
    patrol_count = fields.Integer(compute='_compute_patrol_count', string='Patrol Count')
    last_check_status = fields.Selection([
        ('on_time', 'On Time'),
        ('late', 'Late'),
        ('missed', 'Missed'),
        ('not_due', 'Not Due Yet')
    ], compute='_compute_check_status', string='Last Check Status', store=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    location_description = fields.Text(string='Location Description')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('code_uniq', 'UNIQUE(code)', 'Point Code must be unique!'),
    ]

    @api.depends('patrol_log_ids')
    def _compute_log_count(self):
        for point in self:
            point.log_count = len(point.patrol_log_ids)

    @api.depends('last_check_time', 'check_interval')
    def _compute_next_check_time(self):
        for point in self:
            if point.check_interval and point.last_check_time:
                hours = point.check_interval
                point.next_check_time = point.last_check_time + timedelta(hours=hours)
            else:
                point.next_check_time = False

    @api.depends('last_check_time', 'next_check_time')
    def _compute_check_status(self):
        now = fields.Datetime.now()
        for point in self:
            if not point.last_check_time or not point.next_check_time:
                point.last_check_status = 'not_due'
                continue

            if point.last_check_time > point.next_check_time - timedelta(minutes=15):
                point.last_check_status = 'on_time'
            elif point.last_check_time <= point.next_check_time:
                point.last_check_status = 'late'
            elif now > point.next_check_time + timedelta(hours=1):
                point.last_check_status = 'missed'
            else:
                point.last_check_status = 'not_due'

    @api.depends()
    def _compute_patrol_count(self):
        for point in self:
            point.patrol_count = self.env['security.patrol'].search_count([
                ('route_id.point_ids', 'in', point.id)
            ])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code'):
                vals['code'] = self.env['ir.sequence'].next_by_code('security.patrol.point') or _('New')

            if not vals.get('barcode'):
                vals['barcode'] = self._generate_unique_code('barcode')

            if not vals.get('qr_code_text'):
                vals['qr_code_text'] = self._generate_unique_code('qrcode')

            if not vals.get('qr_code') and vals.get('qr_code_text'):
                qr_code_data = vals.get('qr_code_text')
                vals['qr_code'] = self._generate_qr_code_image(qr_code_data)

        return super().create(vals_list)

    def _generate_unique_code(self, code_type):
        """Generate a unique code for barcode or QR code"""
        prefix = 'PP-' if code_type == 'barcode' else 'QRPP-'

        # Generate random alphanumeric code
        chars = string.ascii_uppercase + string.digits
        code = prefix + ''.join(random.choice(chars) for _ in range(8))

        # Check if code exists
        existing_domain = [('barcode', '=', code)] if code_type == 'barcode' else [('qr_code_text', '=', code)]
        while self.search_count(existing_domain):
            code = prefix + ''.join(random.choice(chars) for _ in range(8))
            existing_domain = [('barcode', '=', code)] if code_type == 'barcode' else [('qr_code_text', '=', code)]

        return code

    def _generate_qr_code_image(self, data):
        """Generate QR code image from data"""
        if not data:
            return False

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_image = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return qr_image

    def action_generate_qr_code(self):
        """Generate QR Code for the patrol point"""
        for record in self:
            record.qr_code_text = record._generate_unique_code('qrcode')
            record.qr_code = record._generate_qr_code_image(record.qr_code_text)

    def action_view_logs(self):
        self.ensure_one()
        return {
            'name': _('Patrol Logs'),
            'view_mode': 'tree,form',
            'res_model': 'security.patrol.log',
            'domain': [('point_id', '=', self.id)],
            'type': 'ir.actions.act_window',
        }

    def action_view_patrols(self):
        self.ensure_one()
        return {
            'name': _('Patrols'),
            'view_mode': 'tree,form',
            'res_model': 'security.patrol',
            'domain': [('route_id.point_ids', 'in', self.id)],
            'type': 'ir.actions.act_window',
        }

    @api.model
    def process_qr_code(self, qr_code):
        """Process QR code scan for patrol check-in"""
        # Find patrol point by QR code
        patrol_point = self.search([
            ('qr_code_text', '=', qr_code),
            ('active', '=', True)
        ], limit=1)

        if not patrol_point:
            # Try to find by barcode as fallback
            patrol_point = self.search([
                ('barcode', '=', qr_code),
                ('active', '=', True)
            ], limit=1)

        if not patrol_point:
            return {'error': _("QR code not recognized as a valid patrol point.")}

        # Return information about the patrol point
        location_parts = []
        if patrol_point.premise_id:
            location_parts.append(patrol_point.premise_id.name)
        if patrol_point.floor_id:
            location_parts.append(patrol_point.floor_id.name)
        if patrol_point.unit_id:
            location_parts.append(patrol_point.unit_id.name)

        location = ' / '.join(location_parts) if location_parts else _('No location specified')

        return {
            'type': 'patrol_point',
            'id': patrol_point.id,
            'name': patrol_point.name,
            'code': patrol_point.code,
            'location': location,
            'point_type': dict(patrol_point._fields['point_type'].selection).get(patrol_point.point_type),
            'last_check_time': patrol_point.last_check_time and fields.Datetime.to_string(patrol_point.last_check_time) or False,
        }

    @api.model
    def process_checkpoint_scan(self, qr_code, patrol_id):
        """Process QR code scan for checkpoint scanning in active patrol with automatic logging"""
        _logger = logging.getLogger(__name__)
        
        # Find patrol point by QR code
        patrol_point = self.search([
            ('qr_code_text', '=', qr_code),
            ('active', '=', True)
        ], limit=1)

        if not patrol_point:
            # Try to find by barcode as fallback
            patrol_point = self.search([
                ('barcode', '=', qr_code),
                ('active', '=', True)
            ], limit=1)

        if not patrol_point:
            return {
                'success': False,
                'error': _("QR code not recognized as a valid checkpoint. Please ensure you're scanning a valid patrol point QR code."),
                'message': _("Invalid QR Code")
            }

        # Get the patrol
        patrol = self.env['security.patrol'].browse(patrol_id)
        if not patrol.exists():
            return {
                'success': False,
                'error': _("Invalid patrol reference. Please contact your supervisor."),
                'message': _("Invalid Patrol")
            }

        if patrol.state != 'in_progress':
            return {
                'success': False,
                'error': _("Patrol is not currently active. Current status: %s") % dict(patrol._fields['state'].selection).get(patrol.state),
                'message': _("Patrol Not Active")
            }

        # Check if the point is part of the patrol route (Requirement 2: exist in the patrol as a checkpoint to be scanned)
        if patrol_point.id not in patrol.point_ids.ids:
            return {
                'success': False,
                'error': _("Checkpoint '%s' is not part of the current patrol route '%s'. Please scan only checkpoints assigned to this patrol.") % (patrol_point.name, patrol.route_id.name),
                'message': _("Checkpoint Not in Route")
            }

        # Check if the point has already been logged in this patrol (Requirement 1: not logged before on that patrol)
        existing_log = self.env['security.patrol.log'].search([
            ('patrol_id', '=', patrol.id),
            ('point_id', '=', patrol_point.id)
        ])

        if existing_log:
            scan_time = fields.Datetime.to_string(existing_log.timestamp)
            return {
                'success': False,
                'error': _("Checkpoint '%s' has already been scanned in this patrol at %s. Each checkpoint can only be scanned once per patrol.") % (patrol_point.name, scan_time),
                'message': _("Already Scanned"),
                'previous_scan_time': scan_time,
                'previous_scan_guard': existing_log.guard_id.name if existing_log.guard_id else ''
            }

        # AUTOMATIC CHECKPOINT LOGGING
        # Both requirements are met:
        # 1. Checkpoint is not logged before on this patrol (checked above)
        # 2. Checkpoint exists in the patrol as a checkpoint to be scanned (checked above)
        # Therefore, automatically create the patrol log
        try:
            current_time = fields.Datetime.now()
            
            # Get security employee from guard
            security_employee = patrol.guard_id.security_employee_id if hasattr(patrol.guard_id, 'security_employee_id') else None
            if not security_employee and hasattr(patrol.guard_id, 'employee_id'):
                # Try to find security employee from regular employee
                security_employee = self.env['security.employee'].search([
                    ('employee_id', '=', patrol.guard_id.employee_id.id)
                ], limit=1)
            
            log_vals = {
                'patrol_id': patrol.id,
                'point_id': patrol_point.id,
                'guard_id': patrol.guard_id.id,
                'timestamp': current_time,
                'notes': _("Automatically logged via QR code scan - checkpoint identified and validated"),
                'company_id': patrol.company_id.id,
            }
            
            # Add security_employee_id if found
            if security_employee:
                log_vals['security_employee_id'] = security_employee.id
            else:
                # If no security employee found, try to use the guard's related employee
                if hasattr(patrol.guard_id, 'employee_id') and patrol.guard_id.employee_id:
                    # Create a basic security employee record if needed
                    security_employee = self.env['security.employee'].create({
                        'name': patrol.guard_id.name,
                        'employee_id': patrol.guard_id.employee_id.id,
                        'company_id': patrol.company_id.id,
                    })
                    log_vals['security_employee_id'] = security_employee.id

            # Create the patrol log automatically
            log = self.env['security.patrol.log'].create(log_vals)
            _logger.info("AUTOMATIC CHECKPOINT LOGGING: Successfully created patrol log %s for checkpoint %s in patrol %s by guard %s", 
                        log.name, patrol_point.name, patrol.name, patrol.guard_id.name)

            # Update the point's last check time
            patrol_point.write({'last_check_time': current_time})

            # Refresh patrol completion rate
            patrol._compute_completion_rate()
            completion_rate = patrol.completion_rate

            # Get location information for display
            location_parts = []
            if patrol_point.premise_id:
                location_parts.append(patrol_point.premise_id.name)
            if patrol_point.floor_id:
                location_parts.append(patrol_point.floor_id.name)
            if patrol_point.unit_id:
                location_parts.append(patrol_point.unit_id.name)
            
            location_info = ' / '.join(location_parts) if location_parts else _('Location not specified')

            # Log the automatic checkpoint logging event
            _logger.info("CHECKPOINT AUTO-LOGGED: Name=%s, Location=%s, Patrol=%s, Guard=%s, Time=%s", 
                        patrol_point.name, location_info, patrol.name, patrol.guard_id.name, current_time)

            return {
                'success': True,
                'checkpoint_name': patrol_point.name,
                'checkpoint_code': patrol_point.code,
                'checkpoint_location': location_info,
                'patrol_name': patrol.name,
                'patrol_route': patrol.route_id.name,
                'guard_name': patrol.guard_id.name,
                'completion_rate': completion_rate,
                'points_completed': patrol.points_covered,
                'points_total': patrol.points_total,
                'scan_time': fields.Datetime.to_string(current_time),
                'log_id': log.id,
                'message': _("Checkpoint '%s' automatically scanned and logged!") % patrol_point.name,
                'auto_logged': True  # Flag to indicate automatic logging occurred
            }

        except Exception as e:
            _logger.error("AUTOMATIC CHECKPOINT LOGGING ERROR: Failed to create patrol log for checkpoint %s in patrol %s: %s", 
                         patrol_point.name, patrol.name, str(e))
            return {
                'success': False,
                'error': _("Failed to automatically log checkpoint due to system error: %s. Please try again or contact support.") % str(e),
                'message': _("Auto-Logging System Error")
            }


class SecurityPatrolRoute(models.Model):
    _name = 'security.patrol.route'
    _description = 'Patrol Route'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Route Name', required=True, tracking=True)
    premise_id = fields.Many2one('security.premise', string='Premise', required=True, tracking=True)
    client_id = fields.Many2one(related='premise_id.client_id', string='Client', store=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        groups='base.group_multi_company',
        help='Company this route belongs to'
    )
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)

    point_ids = fields.Many2many('security.patrol.point', string='Patrol Points',
                                domain="[('premise_id', '=', premise_id or False), '|', ('company_id', '=', company_id or False), ('company_id', '=', False)]")
    team_ids = fields.Many2many('security.team', string='Assigned Teams')

    # Schedule fields
    frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('custom', 'Custom')
    ], string='Frequency', default='daily', required=True)

    days_of_week = fields.Many2many('security.day', string='Days of Week')
    start_time = fields.Float(string='Start Time')
    end_time = fields.Float(string='End Time')
    duration = fields.Float(string='Expected Duration (Hours)', compute='_compute_duration')

    patrol_count = fields.Integer(compute='_compute_patrol_count', string='Completed Patrols')
    point_count = fields.Integer(compute='_compute_point_count', string='Points')
    color = fields.Integer(string='Color')

    @api.depends('point_ids')
    def _compute_point_count(self):
        for route in self:
            route.point_count = len(route.point_ids)

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for route in self:
            if route.end_time >= route.start_time:
                route.duration = route.end_time - route.start_time
            else:
                # Handle cases where end time is on the next day
                route.duration = (24 - route.start_time) + route.end_time

    def _compute_patrol_count(self):
        for route in self:
            route.patrol_count = self.env['security.patrol'].search_count([
                ('route_id', '=', route.id),
                ('state', '=', 'completed')
            ])

    def action_view_patrols(self):
        self.ensure_one()
        return {
            'name': _('Patrols'),
            'view_mode': 'tree,form',
            'res_model': 'security.patrol',
            'domain': [('route_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_route_id': self.id},
        }

    def action_schedule_patrol(self):
        """Open wizard to schedule a patrol for this route"""
        self.ensure_one()
        return {
            'name': _('Schedule Patrol'),
            'view_mode': 'form',
            'res_model': 'security.patrol.schedule.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'default_route_id': self.id},
        }


class SecurityPatrol(models.Model):
    _name = 'security.patrol'
    _description = 'Security Patrol'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_time desc'

    name = fields.Char(string='Patrol Reference', readonly=True, copy=False)
    route_id = fields.Many2one('security.patrol.route', string='Route', required=True, tracking=True)
    premise_id = fields.Many2one(related='route_id.premise_id', string='Premise', store=True)
    client_id = fields.Many2one(related='premise_id.client_id', string='Client', store=True)

    # Assigned guard
    guard_id = fields.Many2one('security.guard', string='Assigned Guard', required=True, tracking=True)
    team_id = fields.Many2one('security.team', string='Team', tracking=True)

    # Patrol type
    patrol_type = fields.Selection([
        ('routine', 'Routine'),
        ('emergency', 'Emergency'),
        ('special', 'Special'),
        ('follow_up', 'Follow-up')
    ], string='Patrol Type', default='routine', required=True, tracking=True)

    # Time tracking
    scheduled_start = fields.Datetime(string='Scheduled Start', required=True,
                                     default=lambda self: fields.Datetime.now())
    scheduled_end = fields.Datetime(string='Scheduled End', compute='_compute_scheduled_end', store=True)
    start_time = fields.Datetime(string='Actual Start', readonly=True)
    end_time = fields.Datetime(string='Actual End', readonly=True)

    # Status
    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='scheduled', tracking=True)

    # Patrol data
    point_ids = fields.Many2many('security.patrol.point', related='route_id.point_ids', string='Patrol Points')
    patrol_point_ids = fields.Many2many('security.patrol.point', related='point_ids', string='Patrol Points')
    log_ids = fields.One2many('security.patrol.log', 'patrol_id', string='Patrol Logs')
    patrol_log_ids = fields.One2many('security.patrol.log', related='log_ids', string='Patrol Logs')
    notes = fields.Text(string='Notes')

    # Statistics
    points_covered = fields.Integer(compute='_compute_points_covered', string='Points Covered')
    points_total = fields.Integer(compute='_compute_points_total', string='Total Points')
    completion_rate = fields.Float(compute='_compute_completion_rate', string='Completion Rate (%)')
    actual_duration = fields.Float(compute='_compute_actual_duration', string='Actual Duration (Hours)')
    log_count = fields.Integer(compute='_compute_log_count', string='Log Count')
    incident_count = fields.Integer(compute='_compute_incident_count', string='Incident Count')
    actual_start_time = fields.Datetime(string='Actual Start Time', readonly=True)
    actual_end_time = fields.Datetime(string='Actual End Time', readonly=True)
    duration = fields.Float(string='Duration (Hours)', compute='_compute_duration')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for patrol in self:
            if patrol.end_time and patrol.start_time:
                delta = patrol.end_time - patrol.start_time
                patrol.duration = delta.total_seconds() / 3600  # Convert to hours
            else:
                patrol.duration = 0


    @api.depends('log_ids')
    def _compute_log_count(self):
        for patrol in self:
            patrol.log_count = len(patrol.log_ids)

    @api.depends()
    def _compute_incident_count(self):
        for patrol in self:
            patrol.incident_count = self.env['security.incident.report'].search_count([
                ('patrol_id', '=', patrol.id)
            ])

    @api.depends('scheduled_start', 'route_id.duration')
    def _compute_scheduled_end(self):
        for patrol in self:
            if patrol.scheduled_start and patrol.route_id.duration:
                hours = int(patrol.route_id.duration)
                minutes = (patrol.route_id.duration - hours) * 60
                patrol.scheduled_end = patrol.scheduled_start + timedelta(hours=hours, minutes=minutes)
            else:
                patrol.scheduled_end = False

    @api.depends('log_ids', 'point_ids')
    def _compute_points_covered(self):
        for patrol in self:
            covered_points = set(patrol.log_ids.mapped('point_id.id'))
            patrol.points_covered = len(covered_points)

    @api.depends('point_ids')
    def _compute_points_total(self):
        for patrol in self:
            patrol.points_total = len(patrol.point_ids)

    @api.depends('points_covered', 'points_total')
    def _compute_completion_rate(self):
        for patrol in self:
            if patrol.points_total:
                patrol.completion_rate = (patrol.points_covered / patrol.points_total) * 100
            else:
                patrol.completion_rate = 0

    @api.depends('start_time', 'end_time')
    def _compute_actual_duration(self):
        for patrol in self:
            if patrol.start_time and patrol.end_time:
                delta = patrol.end_time - patrol.start_time
                patrol.actual_duration = delta.total_seconds() / 3600  # Convert to hours
            else:
                patrol.actual_duration = 0

    @api.onchange('premise_id')
    def _onchange_premise_id(self):
        """When premise changes, reset route_id to ensure consistency"""
        if self.premise_id and self.route_id and self.route_id.premise_id != self.premise_id:
            self.route_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('security.patrol')
        return super().create(vals_list)

    # models/patrolling.py (continued)
    def action_start(self):
        """Start the patrol"""
        self.ensure_one()
        if self.state != 'scheduled':
            raise UserError(_("Only scheduled patrols can be started"))

        self.write({
            'state': 'in_progress',
            'start_time': fields.Datetime.now(),
        })

        # Notify client (optional)
        if self.client_id and self.client_id.contact_id and self.client_id.contact_id.email:
            template = self.env.ref('security_management.email_template_patrol_started')
            template.send_mail(self.id, force_send=True)

        return True

    @api.model
    def get_dashboard_data(self, *args, **kwargs):
        """
        Get dashboard data for security patrols
        Returns counts of patrols in different states
        """
        _logger = logging.getLogger(__name__)

        # Use proper company context for all operations
        self = self.with_context(company_id=self.env.company.id)

        # Base domain with proper company filtering
        domain = ['|', ('company_id', '=', self.env.company.id), ('company_id', 'in', self.env.companies.ids)]

        # Get all patrols for debugging
        all_patrol_records = self.search(domain)
        _logger.info("All patrol records: %s with states: %s",
                    all_patrol_records.mapped('name'),
                    dict(zip(all_patrol_records.mapped('name'), all_patrol_records.mapped('state'))))

        # Get counts for different patrol states
        all_patrols = len(all_patrol_records)
        scheduled = self.search_count(domain + [('state', '=', 'scheduled')])

        # Check for in-progress patrols with detailed logging
        in_progress_patrols = self.search(domain + [('state', '=', 'in_progress')])
        in_progress = len(in_progress_patrols)
        _logger.info("In-progress patrol records: %s", in_progress_patrols.mapped('name'))

        completed = self.search_count(domain + [('state', '=', 'completed')])
        cancelled = self.search_count(domain + [('state', '=', 'cancelled')])

        # Get counts for today's patrols
        today = fields.Date.today()
        today_start = datetime.combine(today, time.min)
        today_end = datetime.combine(today, time.max)

        # Domain for patrols scheduled today
        today_scheduled_domain = domain + [
            ('scheduled_start', '>=', fields.Datetime.to_string(today_start)),
            ('scheduled_start', '<=', fields.Datetime.to_string(today_end))
        ]

        # Domain for patrols completed today (based on end_time)
        today_completed_domain = domain + [
            ('state', '=', 'completed'),
            ('end_time', '>=', fields.Datetime.to_string(today_start)),
            ('end_time', '<=', fields.Datetime.to_string(today_end))
        ]

        today_records = self.search(today_scheduled_domain)
        _logger.info("Today's patrol records: %s", today_records.mapped('name'))

        # Get completed patrols for today
        today_completed_records = self.search(today_completed_domain)
        _logger.info("Today's completed patrol records: %s", today_completed_records.mapped('name'))

        today_total = len(today_records)
        today_completed = len(today_completed_records)
        today_in_progress = self.search_count(today_scheduled_domain + [('state', '=', 'in_progress')])

        # Calculate completion percentage
        completion_percentage = 0
        if today_total > 0:
            completion_percentage = round((today_completed / today_total) * 100)

        # Get active patrols for display
        active_patrols = []
        for patrol in in_progress_patrols:
            active_patrols.append({
                'id': patrol.id,
                'name': patrol.name,
                'guard_name': patrol.guard_id.name if patrol.guard_id else '',
                'route': patrol.route_id.name if patrol.route_id else '',
                'start_time': fields.Datetime.to_string(patrol.start_time) if patrol.start_time else '',
                'completion_rate': patrol.completion_rate,
                'state': patrol.state,
            })

        # Get upcoming patrols
        now = fields.Datetime.now()

        # First try to get scheduled patrols from now onwards
        upcoming_domain = domain + [
            ('state', '=', 'scheduled'),
            ('scheduled_start', '>=', fields.Datetime.to_string(now))
        ]
        upcoming_patrols_records = self.search(upcoming_domain, order='scheduled_start asc', limit=10)
        _logger.info("Upcoming patrol records: %s with domain: %s",
                    upcoming_patrols_records.mapped('name'), upcoming_domain)

        # If no upcoming patrols found, try with a more lenient domain
        if not upcoming_patrols_records:
            # Try to find any scheduled patrols
            lenient_domain = domain + [
                ('state', '=', 'scheduled'),
            ]
            upcoming_patrols_records = self.search(lenient_domain, order='scheduled_start asc', limit=10)
            _logger.info("Lenient upcoming patrol records: %s", upcoming_patrols_records.mapped('name'))

            # If still no records, try to include recently scheduled patrols from today
            if not upcoming_patrols_records:
                today_scheduled = domain + [
                    ('state', '=', 'scheduled'),
                    ('scheduled_start', '>=', fields.Datetime.to_string(today_start)),
                    ('scheduled_start', '<=', fields.Datetime.to_string(today_end))
                ]
                upcoming_patrols_records = self.search(today_scheduled, order='scheduled_start asc', limit=10)
                _logger.info("Today's scheduled patrol records: %s", upcoming_patrols_records.mapped('name'))

        upcoming_patrols = []
        for patrol in upcoming_patrols_records:
            upcoming_patrols.append({
                'id': patrol.id,
                'name': patrol.name,
                'guard_name': patrol.guard_id.name if patrol.guard_id else '',
                'route_name': patrol.route_id.name if patrol.route_id else '',
                'scheduled_start': fields.Datetime.to_string(patrol.scheduled_start) if patrol.scheduled_start else '',
            })

        # Calculate point coverage statistics
        point_coverage = {}

        # Get all patrol points
        all_points = self.env['security.patrol.point'].with_context(company_id=self.env.company.id).search([
            '|', ('company_id', '=', self.env.company.id), ('company_id', 'in', self.env.companies.ids)
        ])

        # Get points covered in the last 7 days
        last_week = now - timedelta(days=7)
        recent_logs = self.env['security.patrol.log'].with_context(company_id=self.env.company.id).search([
            ('create_date', '>=', fields.Datetime.to_string(last_week)),
            '|', ('company_id', '=', self.env.company.id), ('company_id', 'in', self.env.companies.ids)
        ])

        # Group points by day
        for i in range(7):
            day = now - timedelta(days=i)
            day_start = datetime.combine(day.date(), time.min)
            day_end = datetime.combine(day.date(), time.max)

            # Count points covered on this day
            day_logs = recent_logs.filtered(lambda l:
                fields.Datetime.from_string(l.create_date) >= day_start and
                fields.Datetime.from_string(l.create_date) <= day_end
            )

            # Use day name as key (e.g., "Monday")
            day_name = day.strftime('%A')
            point_coverage[day_name] = len(day_logs)

        # Add patrol stats for the chart
        patrol_stats = {
            'completed': completed,
            'in_progress': in_progress,
            'scheduled': scheduled,
            'cancelled': cancelled
        }

        return {
            'total_patrols': all_patrols,
            'scheduled': scheduled,
            'in_progress': in_progress,
            'completed': completed,
            'cancelled': cancelled,
            'completed_today': today_completed,
            'today_total': today_total,
            'today_in_progress': today_in_progress,
            'completion_percentage': completion_percentage,
            'active_patrols': active_patrols,
            'upcoming_patrols': upcoming_patrols,
            'point_coverage': point_coverage,
            'patrol_stats': patrol_stats,
        }
    def _show_incomplete_patrol_warning(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Patrol Incomplete'),
                'message': _('The patrol has uncovered points. Please complete the patrol.'),
                'type': 'warning',
                'sticky': False,
            }
        }
    def action_complete(self):
        """Complete a patrol"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_("Only in-progress patrols can be completed"))

        # Check if all patrol points have been covered
        uncovered_points = self.get_uncovered_points()
        if uncovered_points:
            # raise warning that the patrol is incomplete
            return self._show_incomplete_patrol_warning()
        else:
            # All points covered, complete directly
            return self._complete_patrol()

    def get_uncovered_points(self):
        """Get points that have not been covered in this patrol"""
        self.ensure_one()

        # Get all points in the route
        all_points = self.point_ids

        # Get points that have been logged
        logged_points = self.log_ids.mapped('point_id')

        # Return points that haven't been logged
        return all_points - logged_points

    def action_scan_point(self):
        """Open QR scanner for patrol points"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_("Only in-progress patrols can scan points"))

        # Use proper company context
        self = self.with_context(company_id=self.env.company.id)

        # Open the patrol log scan form
        return {
            'name': _('Scan Patrol Point'),
            'type': 'ir.actions.act_window',
            'res_model': 'security.patrol.log',
            'view_mode': 'form',
            'view_id': self.env.ref('security_management.view_security_patrol_log_scan_form').id,
            'target': 'new',
            'context': {
                'default_patrol_id': self.id,
                'default_guard_id': self.guard_id.id,
                'company_id': self.company_id.id,
            },
        }

    def _complete_patrol(self):
        """Internal method to complete the patrol"""
        # Use proper company context for this operation
        self = self.with_context(company_id=self.env.company.id)

        # Check for uncovered points and create logs for them if needed
        uncovered_points = self.get_uncovered_points()
        if uncovered_points:
            _logger = logging.getLogger(__name__)
            _logger.info("Creating logs for %s uncovered points during patrol completion", len(uncovered_points))

            # Create logs for uncovered points with the guard from the patrol
            for point in uncovered_points:
                self.env['security.patrol.log'].with_context(company_id=self.env.company.id).create({
                    'patrol_id': self.id,
                    'point_id': point.id,
                    'guard_id': self.guard_id.id,  # Explicitly set the guard_id from the patrol
                    'timestamp': fields.Datetime.now(),
                    'notes': _("Automatically logged during patrol completion"),
                })

        # Update patrol state and times
        self.write({
            'state': 'completed',
            'end_time': fields.Datetime.now(),
            'actual_end_time': fields.Datetime.now(),
            'duration': self._compute_patrol_duration(),
        })

        # Update last check time for all scanned points
        scanned_points = self.log_ids.mapped('point_id')
        if scanned_points:
            scanned_points.write({'last_check_time': fields.Datetime.now()})

        # Log a message
        self.message_post(body=_("Patrol completed successfully"))

        # Return an action to reload the patrol dashboard
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {
                'menu_id': self.env.ref('security_management.menu_security_patrol_dashboard').id
            }
        }

    def _compute_patrol_duration(self):
        """Compute the duration of the patrol in hours"""
        self.ensure_one()
        if not self.start_time:
            return 0.0

        end_time = fields.Datetime.now()
        start_time = self.start_time

        # Calculate duration in hours
        duration_timedelta = end_time - start_time
        duration_hours = duration_timedelta.total_seconds() / 3600.0

        return round(duration_hours, 2)

    def action_cancel(self):
        """Cancel the patrol"""
        self.ensure_one()
        if self.state in ['completed']:
            raise UserError(_("Completed patrols cannot be cancelled"))

        self.write({
            'state': 'cancelled',
        })
        return True

    def action_view_logs(self):
        self.ensure_one()
        return {
            'name': _('Patrol Logs'),
            'view_mode': 'tree,form',
            'res_model': 'security.patrol.log',
            'domain': [('patrol_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_patrol_id': self.id},
        }

    def action_view_incidents(self):
        self.ensure_one()
        return {
            'name': _('Incidents'),
            'view_mode': 'tree,form',
            'res_model': 'security.incident.report',
            'domain': [('patrol_id', '=', self.id)],
            'type': 'ir.actions.act_window',
        }


class SecurityPatrolLog(models.Model):
    _name = 'security.patrol.log'
    _description = 'Patrol Log'
    _order = 'timestamp desc'

    name = fields.Char(string='Reference', readonly=True, copy=False,
                     default=lambda self: _('New'))
    patrol_id = fields.Many2one('security.patrol', string='Patrol', ondelete='cascade')
    point_id = fields.Many2one('security.patrol.point', string='Patrol Point', required=True)
    patrol_point_id = fields.Many2one('security.patrol.point', related='point_id', string='Patrol Point')
    security_employee_id = fields.Many2one('security.employee', string='Security Employee', required=False)
    guard_id = fields.Many2one('security.guard', string='Guard', required=True)
    timestamp = fields.Datetime(string='Timestamp', default=fields.Datetime.now, required=True)
    date = fields.Date(string='Date', compute='_compute_date', store=True)
    start_time = fields.Datetime(string="Start Time", default=fields.Datetime.now)
    end_time = fields.Datetime(string="End Time")
    premise_id = fields.Many2one(related='point_id.premise_id', string='Premise', store=True)
    floor_id = fields.Many2one(related='point_id.floor_id', string='Floor', store=True)
    unit_id = fields.Many2one(related='point_id.unit_id', string='Unit', store=True)
    client_id = fields.Many2one(related='premise_id.client_id', string='Client', store=True)
    notes = fields.Text(string='Notes')
    issue_detected = fields.Boolean(string='Issue Detected')
    issue_description = fields.Text(string='Issue Description')
    image = fields.Binary(string='Image', attachment=True)
    image_filename = fields.Char(string='Image Filename')
    image_ids = fields.Many2many('ir.attachment', string='Images', copy=False)
    check_time = fields.Datetime(string='Check Time', default=fields.Datetime.now)
    status = fields.Selection([
            ('on_time', 'On Time'),
            ('late', 'Late'),
            ('missed', 'Missed'),
            ('not_due', 'Not Due Yet')
        ], compute='_compute_check_status', string='Last Check Status', store=True)
    note = fields.Text(string='Note')
    location_latitude = fields.Char(string='Location Latitude')
    location_longitude = fields.Char(string='Location Longitude')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        groups='base.group_multi_company',
        help='Company this patrol log belongs to'
    )
    
    @api.model
    def create(self, vals):
        """Create a new patrol log with proper sequence and guard assignment"""
        _logger = logging.getLogger(__name__)

        # Use proper company context
        self = self.with_context(company_id=self.env.company.id)

        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].with_context(company_id=self.env.company.id).next_by_code('security.patrol.log') or _('New')

        # If patrol_id is provided but no guard_id, get the guard from the patrol
        if vals.get('patrol_id') and not vals.get('guard_id'):
            patrol = self.env['security.patrol'].browse(vals['patrol_id'])
            vals['guard_id'] = patrol.guard_id.id
            _logger.info("Assigned guard %s from patrol to log", patrol.guard_id.name)

        # Create the log
        log = super(SecurityPatrolLog, self).create(vals)

        # Update the point's last check time
        if log.point_id:
            log.point_id.write({'last_check_time': log.timestamp})
            _logger.info("Updated last check time for point %s to %s", log.point_id.name, log.timestamp)

        return log

    @api.model
    def create_from_scan(self, point_id, patrol_id=None):
        """Create a patrol log from a QR code scan"""
        _logger = logging.getLogger(__name__)

        # Use proper company context
        self = self.with_context(company_id=self.env.company.id)

        if not patrol_id:
            # Try to find an active patrol for the current user
            user_employee = self.env.user.employee_id
            if not user_employee:
                return {'error': _("You are not linked to an employee record. Please contact your administrator.")}

            active_patrols = self.env['security.patrol'].search([
                ('guard_id', '=', user_employee.security_employee.guard_id.id),
                ('state', '=', 'in_progress'),
                '|', ('company_id', '=', self.env.company.id), ('company_id', '=', False)
            ])

            if not active_patrols:
                return {'error': _("No active patrol found for your user.")}

            patrol_id = active_patrols[0].id

        # Get the patrol and check if the point is part of the route
        patrol = self.env['security.patrol'].browse(patrol_id)
        point = self.env['security.patrol.point'].browse(point_id)

        if not point.exists():
            return {'error': _("Invalid patrol point.")}

        if not patrol.exists():
            return {'error': _("Invalid patrol.")}

        if patrol.state != 'in_progress':
            return {'error': _("Patrol is not in progress.")}

        # Check if the point is part of the patrol route
        if point.id not in patrol.point_ids.ids:
            return {'error': _("This point is not part of the patrol route.")}

        # Check if the point has already been logged in this patrol
        existing_log = self.search([
            ('patrol_id', '=', patrol.id),
            ('point_id', '=', point.id)
        ])

        if existing_log:
            return {'error': _("This point has already been scanned in this patrol.")}

        # Create the log
        log_vals = {
            'patrol_id': patrol.id,
            'point_id': point.id,
            'guard_id': patrol.guard_id.id,
            'timestamp': fields.Datetime.now(),
        }

        log = self.create(log_vals)
        _logger.info("Created patrol log %s for point %s in patrol %s", log.name, point.name, patrol.name)

        return {
            'success': True,
            'log_id': log.id,
            'message': _("Point %s successfully logged.") % point.name
        }

    @api.onchange('patrol_id')
    def _onchange_patrol_id(self):
        """Update domain for point_id based on patrol's points"""
        if self.patrol_id:
            return {'domain': {'point_id': [('id', 'in', self.patrol_id.point_ids.ids)]}}
        return {'domain': {'point_id': []}}

    def action_log_point(self):
        """Action to log a patrol point"""
        self.ensure_one()
        _logger = logging.getLogger(__name__)

        # Use proper company context
        self = self.with_context(company_id=self.env.company.id)

        if not self.patrol_id:
            raise UserError(_("Patrol must be specified"))

        if not self.point_id:
            raise UserError(_("Patrol point must be specified"))

        if not self.guard_id:
            # If guard_id is not set, get it from the patrol
            self.guard_id = self.patrol_id.guard_id

        # Check if the point is part of the patrol route
        if self.point_id.id not in self.patrol_id.point_ids.ids:
            raise UserError(_("This point is not part of the patrol route."))

        # Check if the point has already been logged in this patrol
        existing_log = self.search([
            ('patrol_id', '=', self.patrol_id.id),
            ('point_id', '=', self.point_id.id)
        ])

        if existing_log and existing_log.id != self.id:
            raise UserError(_("This point has already been scanned in this patrol."))

        # Set timestamp if not already set
        if not self.timestamp:
            self.timestamp = fields.Datetime.now()

        # Create the log
        vals = {
            'patrol_id': self.patrol_id.id,
            'point_id': self.point_id.id,
            'guard_id': self.guard_id.id,
            'timestamp': self.timestamp,
            'issue_detected': self.issue_detected,
            'issue_description': self.issue_description,
            'notes': self.notes,
        }

        # If this is a new record, create it
        if self._origin.id:
            # Update existing record
            self.write(vals)
            log = self
        else:
            # Create new record
            log = self.create(vals)

        _logger.info("Logged patrol point %s in patrol %s by guard %s",
                    self.point_id.name, self.patrol_id.name, self.guard_id.name)

        # Show success message and close the form
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _("Point %s successfully logged.") % self.point_id.name,
                'sticky': False,
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def _compute_check_status(self):
        """Compute the check status based on the scheduled time"""
        for log in self:
            if not log.point_id or not log.point_id.check_interval:
                log.status = 'on_time'
                continue

            # If the point has a next check time, use it to determine status
            if log.point_id.next_check_time:
                check_time = fields.Datetime.from_string(log.timestamp)
                next_due = fields.Datetime.from_string(log.point_id.next_check_time)

                # If checked before due time, it's on time
                if check_time <= next_due:
                    log.status = 'on_time'
                # If checked within 30 minutes of due time, it's late
                elif check_time <= next_due + timedelta(minutes=30):
                    log.status = 'late'
                # If checked more than 30 minutes after due time, it's missed
                else:
                    log.status = 'missed'
            else:
                log.status = 'on_time'

    @api.depends('timestamp')
    def _compute_date(self):
        for log in self:
            log.date = fields.Date.from_string(log.timestamp)


class SecurityDay(models.Model):
    _name = 'security.day'
    _description = 'Day of Week'
    _order = 'sequence'

    name = fields.Char(string='Day Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    day_code = fields.Integer(string='Day Code', help="0 for Monday, 6 for Sunday")
