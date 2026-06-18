from odoo import models, fields, api, _
from datetime import timedelta
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class SecurityClient(models.Model):
    _name = 'security.client'
    _description = 'Security Client'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Client Name', required=True, tracking=True)
    contact_id = fields.Many2one('res.partner', string='Primary Contact', required=True, tracking=True)
    contract_start_date = fields.Date('Contract Start Date', required=True, tracking=True)
    contract_end_date = fields.Date('Contract End Date', required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
    is_available = fields.Boolean(string='Is Available', default=True)
    # Relationships
    security_team_ids = fields.One2many('security.team', 'client_id', string='Security Teams')
    premise_ids = fields.One2many('security.premise', 'client_id', string='Premises')
    contact_ids = fields.One2many('security.contact', 'client_id', string='Contacts')
    gate_pass_ids = fields.One2many('security.gate.pass', 'client_id', string='Gate Passes')
    visit_record_count = fields.Integer(compute='_compute_visit_record_count', string='Visit Records')
    task_ids = fields.One2many('security.task', 'client_id', string='Tasks')
    schedule_ids = fields.One2many('security.schedule', 'client_id', string='Schedules')

    # Computed Fields
    team_count = fields.Integer(compute='_compute_team_count', string='Teams')
    premise_count = fields.Integer(compute='_compute_premise_count', string='Premises')

    @api.depends('gate_pass_ids')
    def _compute_visit_record_count(self):
        for client in self:
            visit_records = self.env['security.visit.record'].search([('gate_pass_id.client_id', '=', client.id)])
            client.visit_record_count = len(visit_records)
    task_count = fields.Integer(compute='_compute_task_count', string='Tasks')
    active_shifts_count = fields.Integer(compute='_compute_active_shifts', string='Active Shifts')
    days_to_expiry = fields.Integer(compute='_compute_days_to_expiry', string='Days to Expiry')
    contract_state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expiring', 'Expiring Soon'),
        ('expired', 'Expired'),
        ('renewed', 'Renewed'),
    ], compute='_compute_contract_state', string='Contract Status', store=True)

    @api.depends('security_team_ids')
    def _compute_team_count(self):
        for client in self:
            client.team_count = len(client.security_team_ids)

    @api.depends('premise_ids')
    def _compute_premise_count(self):
        for client in self:
            client.premise_count = len(client.premise_ids)

    @api.depends('schedule_ids', 'schedule_ids.shift_assignment_ids',
                 'schedule_ids.shift_assignment_ids.date')
    def _compute_active_shifts(self):
        today = fields.Date.today()
        for client in self:
            active_shifts = self.env['security.shift.assignment'].search_count([
                ('schedule_id.client_id', '=', client.id),
                ('date', '=', today)
            ])
            client.active_shifts_count = active_shifts

    @api.depends('contract_end_date')
    def _compute_days_to_expiry(self):
        today = fields.Date.today()
        for client in self:
            if client.contract_end_date:
                delta = client.contract_end_date - today
                client.days_to_expiry = delta.days
            else:
                client.days_to_expiry = 0

    @api.depends('contract_start_date', 'contract_end_date', 'days_to_expiry')
    def _compute_contract_state(self):
        today = fields.Date.today()
        for client in self:
            if not client.contract_start_date or not client.contract_end_date:
                client.contract_state = 'draft'
            elif client.contract_end_date < today:
                client.contract_state = 'expired'
            elif client.days_to_expiry <= 30:
                client.contract_state = 'expiring'
            elif client.contract_start_date <= today <= client.contract_end_date:
                client.contract_state = 'active'
            else:
                client.contract_state = 'draft'

    @api.constrains('contract_start_date', 'contract_end_date')
    def _check_dates(self):
        for record in self:
            if record.contract_start_date and record.contract_end_date:
                if record.contract_start_date > record.contract_end_date:
                    raise ValidationError(_("Contract end date must be after start date"))

    def action_view_premises(self):
        self.ensure_one()
        return {
            'name': _('Premises'),
            'res_model': 'security.premise',
            'view_mode': 'tree,form',
            'domain': [('client_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_client_id': self.id},
        }

    def action_view_teams(self):
        self.ensure_one()
        return {
            'name': _('Security Teams'),
            'res_model': 'security.team',
            'view_mode': 'tree,form',
            'domain': [('client_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_client_id': self.id},
        }

    def action_send_expiry_notification(self):
        """Send notification email about contract expiry"""
        # Try to find the email template with the correct module name
        template = self.env.ref('security_management.email_template_contract_expiry', raise_if_not_found=False)

        # If template not found, log a warning and return
        if not template:
            _logger.warning("Email template 'security_management.email_template_contract_expiry' not found. Notification not sent.")
            return

        for client in self:
            if client.contract_state in ['expiring', 'expired']:
                template.send_mail(client.id, force_send=True)

    def extend_contract(self, months=12):
        """Extend contract by specified number of months"""
        self.ensure_one()
        if self.contract_end_date:
            old_date = self.contract_end_date
            new_date = self.contract_end_date + timedelta(days=30 * months)
            self.write({'contract_end_date': new_date})

            # Log the change
            self.message_post(body=_(
                f"Contract extended from {old_date} to {new_date} ({months} months)"
            ))

    def action_view_tasks(self):
        self.ensure_one()
        return {
            'name': _('Tasks'),
            'res_model': 'security.task',
            'view_mode': 'tree,form',
            'domain': [('client_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_client_id': self.id},
        }

    @api.depends('task_ids')
    def _compute_task_count(self):
        for client in self:
            client.task_count = len(client.task_ids)
