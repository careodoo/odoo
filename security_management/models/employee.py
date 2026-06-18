from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SecurityEmployee(models.Model):
    _name = 'security.employee'
    _description = 'Security Employee'
    _inherits = {'hr.employee': 'employee_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Employee Name', required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, ondelete='cascade')
    employee_code = fields.Char(string='Employee Code', required=True, tracking=True, copy=False)
    badge_number = fields.Char(string='Badge Number', tracking=True)
    license_number = fields.Char(string='License Number', tracking=True)
    license_expiry = fields.Date(string='License Expiry', tracking=True)

    # Security specific fields
    is_team_leader = fields.Boolean(string='Is Team Leader', default=False, tracking=True)
    security_rank = fields.Selection([
        ('guard', 'Security Guard'),
        ('supervisor', 'Supervisor'),
        ('manager', 'Security Manager'),
        ('director', 'Security Director')
    ], string='Security Rank', default='guard', tracking=True)

    # Skills and certifications
    skill_ids = fields.Many2many('security.skill', string='Skills')
    certification_ids = fields.One2many('security.certification', 'security_employee_id', string='Certifications')

    # Relationships
    team_ids = fields.Many2many('security.team', string='Security Teams')
    
    # Company related fields
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    patrol_log_ids = fields.One2many('security.patrol.log', 'security_employee_id', string='Patrol Logs')
    key_log_ids = fields.One2many('security.key.log', 'security_employee_id', string='Key Logs')
    shift_assignment_ids = fields.One2many('security.shift.assignment', 'security_employee_id', string='Shift Assignments')

    # Computed fields
    active_task_count = fields.Integer(compute='_compute_active_task_count', string='Active Tasks')
    patrol_count = fields.Integer(compute='_compute_patrol_count', string='Patrol Count')
    current_shift_id = fields.Many2one('security.shift.assignment', compute='_compute_current_shift', string='Current Shift')
    role_id = fields.Many2one('security.role', string='Role', required=True)
    phone = fields.Char(string='Phone', tracking=True)
    email = fields.Char(string='Email', tracking=True)
    is_available = fields.Boolean(string='Is Available', default=True, tracking=True)
    image_1920 = fields.Image(string='Image', max_width=1920, max_height=1920)
    
    def _compute_active_task_count(self):
        for employee in self:
            # Get tasks from security.guard relationship where guard is linked to this employee
            employee.active_task_count = self.env['security.task'].search_count([
                ('assigned_to.security_employee_id', '=', employee.id),
                ('state', 'not in', ['completed', 'refused'])
            ])

    @api.depends('patrol_log_ids')
    def _compute_patrol_count(self):
        for employee in self:
            employee.patrol_count = len(employee.patrol_log_ids)

    @api.depends('shift_assignment_ids')
    def _compute_current_shift(self):
        today = fields.Date.today()
        for employee in self:
            current_shift = self.env['security.shift.assignment'].search([
                ('security_employee_id', '=', employee.id),
                ('date', '=', today),
                ('state', '=', 'confirmed')
            ], limit=1)
            employee.current_shift_id = current_shift.id if current_shift else False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('employee_code'):
                vals['employee_code'] = self.env['ir.sequence'].next_by_code('security.employee')
        return super().create(vals_list)

    def action_create_security_guard(self):
        """Create a security guard from this employee"""
        guard = self.env['security.guard'].create({
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'badge_number': self.badge_number,
            'license_number': self.license_number,
            'license_expiry': self.license_expiry,
            'security_employee_id': self.id,
            'security_employee_role_id': self.role_id.id,
            'security_employee_team_ids': [(6, 0, self.team_ids.ids)] if self.team_ids else False,
            'skill_ids': [(6, 0, self.skill_ids.ids)] if self.skill_ids else False,
            'is_available': self.is_available,
            'status': 'active',
        })

        # Copy certifications
        for cert in self.certification_ids:
            self.env['security.certification'].create({
                'name': cert.name,
                'certification_number': cert.certification_number,
                'issue_date': cert.issue_date,
                'expiry_date': cert.expiry_date,
                'issuing_authority': cert.issuing_authority,
                'guard_id': guard.id,
            })

        # Return action to open the newly created guard
        return {
            'name': _('Security Guard Created'),
            'view_mode': 'form',
            'res_model': 'security.guard',
            'res_id': guard.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    def action_view_tasks(self):
        self.ensure_one()
        return {
            'name': _('Tasks'),
            'view_mode': 'tree,form',
            'res_model': 'security.task',
            'domain': [('assigned_to', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_assigned_to': self.id},
        }

    def action_view_patrols(self):
        self.ensure_one()
        return {
            'name': _('Patrol Logs'),
            'view_mode': 'tree,form',
            'res_model': 'security.patrol.log',
            'domain': [('security_employee_id', '=', self.id)],
            'type': 'ir.actions.act_window',
        }

    def action_view_shifts(self):
        self.ensure_one()
        return {
            'name': _('Shift Assignments'),
            'view_mode': 'tree,form,calendar',
            'res_model': 'security.shift.assignment',
            'domain': [('security_employee_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_security_employee_id': self.id},
        }

    def action_view_key_logs(self):
        self.ensure_one()
        return {
            'name': _('Key Logs'),
            'view_mode': 'tree,form',
            'res_model': 'security.key.log',
            'domain': [('security_employee_id', '=', self.id)],
            'type': 'ir.actions.act_window',
        }

    def action_generate_performance_report(self):
        """Generate performance report for the employee"""
        self.ensure_one()
        return self.env.ref('security_management.action_report_security_employee').report_action(self)


class SecuritySkill(models.Model):
    _name = 'security.skill'
    _description = 'Security Skill'

    name = fields.Char(string='Skill Name', required=True)
    description = fields.Text(string='Description')

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Skill name must be unique!')
    ]
