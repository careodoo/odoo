from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime


class SecurityTeam(models.Model):
    _name = 'security.team'
    _description = 'Security Team'

    @api.model
    def get_dashboard_data(self):
        """Get data for the security dashboard"""
        import logging
        _logger = logging.getLogger(__name__)
        
        try:
            # Initialize default values
            client_count = 0
            post_site_count = 0
            guard_count = 0
            user_count = 0
            checkin_count = 0
            clockin_count = 0
            guards = []
            
            # Get client count safely
            try:
                client_count = self.env['security.client'].search_count([])
            except Exception as e:
                _logger.error("Error getting client count: %s", str(e))
            
            # Get post site count safely
            try:
                if 'security.post.site' in self.env:
                    post_site_count = self.env['security.post.site'].search_count([])
            except Exception as e:
                _logger.error("Error getting post site count: %s", str(e))
            
            # Get security guard count safely
            try:
                guard_count = self.env['security.employee'].search_count([])
            except Exception as e:
                _logger.error("Error getting guard count: %s", str(e))
                
            # Get back office team count safely
            try:
                security_manager_group = self.env.ref('security_management.group_security_manager', False)
                if security_manager_group:
                    user_count = len(security_manager_group.users)
            except Exception as e:
                _logger.error("Error getting user count: %s", str(e))
            
            # Get check-ins and clock-ins for today safely
            try:
                today = fields.Date.today()
                if 'security.checkin' in self.env:
                    checkin_count = self.env['security.checkin'].search_count([('date', '=', today)])
            except Exception as e:
                _logger.error("Error getting checkin count: %s", str(e))
                
            try:
                if 'security.clockin' in self.env:
                    clockin_count = self.env['security.clockin'].search_count([('date', '=', today)])
            except Exception as e:
                _logger.error("Error getting clockin count: %s", str(e))
            
            # Get guard data safely
            try:
                security_employees = self.env['security.employee'].search([], limit=10)
                
                for employee in security_employees:
                    # Default values
                    guard_data = {
                        'id': employee.id,
                        'name': employee.name,
                        'image': '/web/image?model=security.employee&field=image_1920&id=%s' % employee.id,
                        'status': 'inactive',
                        'post_site': 'N/A',
                        'last_updated': 'N/A',
                        'battery': 'N/A',
                        'speed': 'N/A',
                        'location': 'N/A',
                        'latitude': 0,
                        'longitude': 0,
                        'model': 'security.employee',
                    }
                    
                    # Try to get latest patrol log for location data
                    try:
                        if 'security.patrol.log' in self.env:
                            latest_patrol = self.env['security.patrol.log'].search([
                                ('guard_id', '=', employee.security_employee_id.guard_id.id)
                            ], limit=1, order='date desc, create_date desc')
                            
                            if latest_patrol:
                                # Use safe attribute checks
                                if hasattr(latest_patrol, 'latitude'):
                                    guard_data['latitude'] = latest_patrol.latitude or 0
                                if hasattr(latest_patrol, 'longitude'):
                                    guard_data['longitude'] = latest_patrol.longitude or 0
                                if hasattr(latest_patrol, 'location'):
                                    guard_data['location'] = latest_patrol.location or 'N/A'
                                if latest_patrol.create_date:
                                    guard_data['last_updated'] = latest_patrol.create_date.strftime('%b %d, %Y')
                    except Exception as e:
                        _logger.error("Error getting patrol data for employee %s: %s", employee.name, str(e))
                    
                    # Get team assignment safely
                    try:
                        if hasattr(employee, 'team_ids') and employee.team_ids:
                            team = employee.team_ids[0]
                            if hasattr(team, 'premise_id') and team.premise_id:
                                guard_data['post_site'] = team.premise_id.name
                            elif hasattr(team, 'client_id') and team.client_id:
                                guard_data['post_site'] = team.client_id.name
                    except Exception as e:
                        _logger.error("Error getting team data for employee %s: %s", employee.name, str(e))
                    
                    # Determine status based on availability
                    try:
                        if hasattr(employee, 'is_available'):
                            guard_data['status'] = 'active' if employee.is_available else 'inactive'
                    except Exception as e:
                        _logger.error("Error getting status for employee %s: %s", employee.name, str(e))
                    
                    guards.append(guard_data)
            except Exception as e:
                _logger.error("Error processing security employees: %s", str(e))
                
            # Add some sample data if no guards are found, to make map usable for testing
            if not guards:
                _logger.info("No guards found, adding sample data for map testing")
                guards = [{
                    'id': 1,
                    'name': 'Sample Guard 1',
                    'status': 'active',
                    'post_site': 'Sample Location',
                    'last_updated': fields.Datetime.now().strftime('%b %d, %Y'),
                    'battery': '80%',
                    'speed': '0 km/h',
                    'location': 'Main Entrance',
                    'latitude': 24.7136,  # Sample coordinates
                    'longitude': 46.6753,  # Sample coordinates
                    'model': 'security.employee'
                }, {
                    'id': 2,
                    'name': 'Sample Guard 2',
                    'status': 'active',
                    'post_site': 'Sample Location 2',
                    'last_updated': fields.Datetime.now().strftime('%b %d, %Y'),
                    'battery': '75%',
                    'speed': '1 km/h',
                    'location': 'Side Entrance',
                    'latitude': 24.7145,  # Sample coordinates
                    'longitude': 46.6780,  # Sample coordinates
                    'model': 'security.employee'
                }]
                
            return {
                'client_count': client_count,
                'post_site_count': post_site_count,
                'guard_count': guard_count,
                'user_count': user_count,
                'checkin_count': checkin_count,
                'clockin_count': clockin_count,
                'guards': guards,
            }
            
        except Exception as e:
            _logger.exception("Unexpected error in security dashboard data: %s", str(e))
            # Return minimal data structure to prevent frontend errors
            return {
                'client_count': 0,
                'post_site_count': 0,
                'guard_count': 0,
                'user_count': 0,
                'checkin_count': 0,
                'clockin_count': 0,
                'guards': [],
                'error': str(e)
            }

    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Team Name', required=True, tracking=True)
    code = fields.Char(string='Team Code', required=True, tracking=True, copy=False)
    client_id = fields.Many2one('security.client', string='Client', required=True, tracking=True)
    leader_id = fields.Many2one('security.employee', string='Team Leader', tracking=True)
    member_ids = fields.Many2many('security.employee', string='Team Members', tracking=True)
    description = fields.Text(string='Description', tracking=True)
    active = fields.Boolean(default=True)

    # Image fields
    image = fields.Binary(string='Team Image', attachment=True)

    # Computed fields
    member_count = fields.Integer(compute='_compute_member_count', string='Member Count')
    task_count = fields.Integer(compute='_compute_task_count', string='Task Count')
    patrol_count = fields.Integer(compute='_compute_patrol_count', string='Patrol Count')
    schedule_count = fields.Integer(compute='_compute_schedule_count', string='Schedule Count')
    premise_id = fields.Many2one('security.premise', string='Premise', tracking=True)
    team_type = fields.Selection([
        ('day', 'Day'),
        ('night', 'Night')
    ], string='Team Type', required=True, default='day')
    color = fields.Integer(string='Color', default=1)
    shift_type_id = fields.Many2one('security.shift.type', string='Shift Type', required=True)
    schedule_ids = fields.Many2many('security.schedule', string='Schedules')
    notes = fields.Text(string='Notes')

    @api.depends('member_ids')
    def _compute_member_count(self):
        for team in self:
            team.member_count = len(team.member_ids)

    @api.depends('member_ids', 'client_id')
    def _compute_task_count(self):
        for team in self:
            team.task_count = self.env['security.task'].search_count([
                '|',
                ('assigned_to', 'in', team.member_ids.ids),
                ('assigned_team_id', '=', team.id)
            ])

    @api.depends('member_ids')
    def _compute_patrol_count(self):
        for team in self:
            team.patrol_count = self.env['security.patrol.log'].search_count([
                ('guard_id', 'in', team.member_ids.security_employee_id.guard_id.ids)
            ])

    @api.depends('member_ids')
    def _compute_schedule_count(self):
        for team in self:
            team.schedule_count = self.env['security.schedule'].search_count([
                ('team_id', '=', team.id)
            ])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code'):
                vals['code'] = self.env['ir.sequence'].next_by_code('security.team')
        return super().create(vals_list)

    def action_assign_members(self):
        """Open wizard to assign team members"""
        self.ensure_one()
        return {
            'name': _('Assign Team Members'),
            'view_mode': 'form',
            'res_model': 'security.team.member.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_team_id': self.id,
                'default_member_ids': [(6, 0, self.member_ids.ids)],
            }
        }

    def action_view_tasks(self):
        """View tasks assigned to team or its members"""
        self.ensure_one()
        return {
            'name': _('Tasks'),
            'view_mode': 'tree,form',
            'res_model': 'security.task',
            'domain': [
                '|',
                ('assigned_to', 'in', self.member_ids.ids),
                ('assigned_team_id', '=', self.id)
            ],
            'type': 'ir.actions.act_window',
            'context': {'default_assigned_team_id': self.id},
        }

    def action_view_patrols(self):
        """View patrol logs for team members"""
        self.ensure_one()
        return {
            'name': _('Patrol Logs'),
            'view_mode': 'tree,form',
            'res_model': 'security.patrol.log',
            'domain': [('guard_id', 'in', self.member_ids.security_employee_id.guard_id.ids)],
            'type': 'ir.actions.act_window',
        }

    def action_view_schedules(self):
        """View schedules for team"""
        self.ensure_one()
        return {
            'name': _('Schedules'),
            'view_mode': 'tree,form',
            'res_model': 'security.schedule',
            'domain': [('team_id', '=', self.id)],
            'type': 'ir.actions.act_window',
        }

    def action_generate_team_report(self):
        """Generate performance report for the team"""
        self.ensure_one()
        return self.env.ref('security_management.action_report_security_team').report_action(self)

    def action_view_members(self):
        """View team members"""
        self.ensure_one()
        return {
            'name': _('Team Members'),
            'view_mode': 'kanban,tree,form',
            'res_model': 'hr.employee',
            'domain': [('id', 'in', self.member_ids.ids)],
            'type': 'ir.actions.act_window',
            'context': {'create': False},
        }
