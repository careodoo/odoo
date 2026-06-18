from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

class SecurityContact(models.Model):
    _name = 'security.contact'
    _description = 'Security Contact'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Contact Name', required=True, tracking=True)
    client_id = fields.Many2one('security.client', string='Client', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Related Partner')

    # Contact details
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    position = fields.Char(string='Position/Role')
    company = fields.Char(string='Company')

    # Availability
    is_available = fields.Boolean(string='Is Available', default=True, tracking=True)

    # Visit count - computed without direct relation
    visit_count = fields.Integer(compute='_compute_visit_count', string='Visit Count', store=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.depends('name', 'email', 'phone')
    def _compute_visit_count(self):
        for contact in self:
            contact.visit_count = self.env['security.visit.record'].search_count([
                ('contact_name', '=', contact.name),
                ('contact_email', '=', contact.email),
                ('contact_phone', '=', contact.phone)
            ])

    def action_view_visits(self):
        self.ensure_one()
        return {
            'name': _('Visits'),
            'view_mode': 'tree,form',
            'res_model': 'security.visit.record',
            'domain': [
                ('contact_name', '=', self.name),
                ('contact_email', '=', self.email),
                ('contact_phone', '=', self.phone)
            ],
            'type': 'ir.actions.act_window',
            'context': {
                'default_contact_name': self.name,
                'default_contact_email': self.email,
                'default_contact_phone': self.phone,
                'default_client_id': self.client_id.id,
            },
        }


class SecurityGatePass(models.Model):
    _name = 'security.gate.pass'
    _description = 'Gate Pass'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Pass Reference', required=True, readonly=True, copy=False,
                     default=lambda self: _('New'))
    client_id = fields.Many2one('security.client', string='Client', required=True, tracking=True)

    # Date and purpose
    start_date = fields.Date(string='Start Date', required=True, tracking=True)
    end_date = fields.Date(string='End Date', required=True, tracking=True)
    purpose = fields.Text(string='Purpose', required=True)

    # Pass type
    pass_type = fields.Selection([
        ('personal', 'Personal'),
        ('vehicle', 'Vehicle')
    ], string='Pass Type', required=True, default='personal', tracking=True)

    # Personal pass details
    person_ids = fields.One2many('security.gate.pass.person', 'gate_pass_id', string='Persons')

    # Vehicle pass details
    vehicle_id = fields.Many2one('security.vehicle', string='Vehicle', tracking=True)

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True, compute='_compute_state', store=True)

    # Approval information
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True)
    approval_date = fields.Datetime(string='Approval Date', readonly=True)

    # Computed fields
    person_count = fields.Integer(compute='_compute_person_count', string='Person Count')
    days_validity = fields.Integer(compute='_compute_days_validity', string='Validity (Days)')
    start_date = fields.Date(string='Start Date', tracking=True)
    end_date = fields.Date(string='End Date', tracking=True)
    person_count = fields.Integer(compute='_compute_person_count', string='Person Count')
    requested_by_id = fields.Many2one('res.users', string='Requested By', readonly=True)
    approval_notes = fields.Text(string='Approval Notes')
    restricted_areas = fields.Text(string='Restricted Areas')

    @api.depends('person_ids')
    def _compute_person_count(self):
        for gate_pass in self:
            gate_pass.person_count = len(gate_pass.person_ids)

    @api.depends('start_date', 'end_date')
    def _compute_days_validity(self):
        for gate_pass in self:
            if gate_pass.start_date and gate_pass.end_date:
                delta = gate_pass.end_date - gate_pass.start_date
                gate_pass.days_validity = delta.days + 1
            else:
                gate_pass.days_validity = 0

    @api.depends('start_date', 'end_date')
    def _compute_state(self):
        today = fields.Date.today()
        for gate_pass in self:
            # Skip computation for cancelled gate passes
            if gate_pass.state == 'cancelled':
                continue

            # If dates are not set, keep as draft
            if not gate_pass.start_date or not gate_pass.end_date:
                gate_pass.state = 'draft'
                continue

            # Skip computation for draft gate passes that haven't been approved yet
            if gate_pass.state == 'draft' and not gate_pass.approved_by:
                continue

            # Determine state based on dates
            if gate_pass.start_date > today:
                gate_pass.state = 'approved'
            elif gate_pass.start_date <= today <= gate_pass.end_date:
                gate_pass.state = 'active'
            elif gate_pass.end_date < today:
                gate_pass.state = 'expired'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('security.gate.pass') or _('New')
        return super().create(vals_list)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for gate_pass in self:
            if gate_pass.start_date and gate_pass.end_date:
                if gate_pass.start_date > gate_pass.end_date:
                    raise ValidationError(_("Gate pass end date must be after start date"))

    # @api.constrains('pass_type', 'person_ids', 'vehicle_id')
    # def _check_pass_details(self):
    #     for gate_pass in self:
    #         if gate_pass.pass_type == 'personal' and not gate_pass.person_ids:
    #             raise ValidationError(_("Please add at least one person for a personal gate pass"))

    #         if gate_pass.pass_type == 'vehicle' and not gate_pass.vehicle_id:
    #             raise ValidationError(_("Please select a vehicle for a vehicle gate pass"))

    def action_approve(self):
        """Approve the gate pass"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Only draft gate passes can be approved"))

        if self.pass_type == 'personal' and not self.person_ids:
            raise UserError(_("Cannot approve a personal gate pass without persons"))

        if self.pass_type == 'vehicle' and not self.vehicle_id:
            raise UserError(_("Cannot approve a vehicle gate pass without a vehicle"))

        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approval_date': fields.Datetime.now(),
        })
        return True

    def action_cancel(self):
        """Cancel the gate pass"""
        self.ensure_one()
        if self.state in ['expired']:
            raise UserError(_("Cannot cancel an expired gate pass"))

        self.write({
            'state': 'cancelled',
        })
        return True

    def action_print_pass(self):
        """Print the gate pass"""
        self.ensure_one()
        if self.state == 'draft':
            raise UserError(_("Cannot print a draft gate pass. Please approve it first."))

        return self.env.ref('security_management.action_report_gate_pass').report_action(self)

    def action_send_email(self):
        """Send gate pass by email"""
        self.ensure_one()

        # Find email template
        template = self.env.ref('security_management.email_template_gate_pass', False)
        if not template:
            raise UserError(_("Email template not found"))

        # Get recipients
        recipients = []
        if self.client_id.contact_id and self.client_id.contact_id.email:
            recipients.append(self.client_id.contact_id.email)

        for person in self.person_ids:
            if person.email:
                recipients.append(person.email)

        if not recipients:
            raise UserError(_("No recipients found to send email"))

        # Send email to each recipient
        for recipient in recipients:
            # Create a context with the recipient email
            ctx = self.env.context.copy()
            ctx.update({
                'email_to': recipient,
            })
            # Send the email with the updated context
            template.with_context(ctx).send_mail(self.id, force_send=True)

        return True

class SecurityGatePassPerson(models.Model):
    _name = 'security.gate.pass.person'
    _description = 'Gate Pass Person'

    gate_pass_id = fields.Many2one('security.gate.pass', string='Gate Pass', required=True, ondelete='cascade')
    name = fields.Char(string='Person Name', required=True)
    id_number = fields.Char(string='ID Number', required=True)
    id_type = fields.Selection([
        ('passport', 'Passport'),
        ('national_id', 'National ID'),
        ('driving_license', 'Driving License'),
        ('other', 'Other')
    ], string='ID Type', default='national_id', required=True)
    phone = fields.Char(string='Phone Number')
    email = fields.Char(string='Email')
    company = fields.Char(string='Company')
    purpose = fields.Text(string='Purpose')

    # Related fields
    client_id = fields.Many2one(related='gate_pass_id.client_id', string='Client', store=True)
    start_date = fields.Date(related='gate_pass_id.start_date', string='Start Date', store=True)
    end_date = fields.Date(related='gate_pass_id.end_date', string='End Date', store=True)
    state = fields.Selection(related='gate_pass_id.state', string='Status', store=True)


class SecurityVehicle(models.Model):
    _name = 'security.vehicle'
    _description = 'Security Vehicle'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Vehicle Description', compute='_compute_name', store=True)
    model = fields.Char(string='Model', required=True, tracking=True)
    vehicle_type = fields.Selection([
        ('car', 'Car'),
        ('truck', 'Truck'),
        ('van', 'Van'),
        ('motorcycle', 'Motorcycle'),
        ('other', 'Other')
    ], string='Type', default='car', required=True, tracking=True)
    license_plate = fields.Char(string='License Plate', required=True, tracking=True)
    color = fields.Char(string='Color')
    owner_name = fields.Char(string='Owner Name')
    year = fields.Char(string='Year')

    # Relationships
    gate_pass_ids = fields.One2many('security.gate.pass', 'vehicle_id', string='Gate Passes')
    gate_pass_count = fields.Integer(compute='_compute_gate_pass_count', string='Gate Pass Count')
    close_check_ids = fields.One2many('security.close.check', 'vehicle_id', string='Close Checks')
    close_check_count = fields.Integer(compute='_compute_close_check_count', string='Close Check Count')

    @api.depends('model', 'license_plate')
    def _compute_name(self):
        for vehicle in self:
            if vehicle.model and vehicle.license_plate:
                vehicle.name = f"{vehicle.model} ({vehicle.license_plate})"
            elif vehicle.license_plate:
                vehicle.name = vehicle.license_plate
            else:
                vehicle.name = "New Vehicle"

    @api.depends('gate_pass_ids')
    def _compute_gate_pass_count(self):
        for vehicle in self:
            vehicle.gate_pass_count = len(vehicle.gate_pass_ids)

    @api.depends('close_check_ids')
    def _compute_close_check_count(self):
        for vehicle in self:
            vehicle.close_check_count = len(vehicle.close_check_ids)

    _sql_constraints = [
        ('plate_number_uniq', 'UNIQUE(license_plate)', 'Vehicle with this plate number already exists!'),
    ]

    def action_view_gate_passes(self):
        self.ensure_one()
        return {
            'name': _('Gate Passes'),
            'view_mode': 'tree,form',
            'res_model': 'security.gate.pass',
            'domain': [('vehicle_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_vehicle_id': self.id, 'default_pass_type': 'vehicle'},
        }

    def action_view_close_checks(self):
        self.ensure_one()
        return {
            'name': _('Close Checks'),
            'view_mode': 'tree,form',
            'res_model': 'security.close.check',
            'domain': [('vehicle_id', '=', self.id)],
            'type': 'ir.actions.act_window',
        }

    def action_create_gate_pass(self):
        """Create a new gate pass for this vehicle"""
        self.ensure_one()
        return {
            'name': _('Create Gate Pass'),
            'view_mode': 'form',
            'res_model': 'security.gate.pass',
            'type': 'ir.actions.act_window',
            'context': {
                'default_vehicle_id': self.id,
                'default_pass_type': 'vehicle',
            },
        }

class SecurityCloseCheck(models.Model):
    _name = 'security.close.check'
    _description = 'Close Check'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'timestamp desc'

    name = fields.Char(string='Check Reference', required=True, readonly=True, copy=False,
                     default=lambda self: _('New'))

    vehicle_id = fields.Many2one('security.vehicle', string='Vehicle', required=True, tracking=True)
    plate_number = fields.Char(string='Plate Number', store=True)
    guard_id = fields.Many2one('security.guard', string='Guard', required=True, tracking=True)
    timestamp = fields.Datetime(string='Timestamp', default=fields.Datetime.now, required=True, tracking=True)

    # Location
    premise_id = fields.Many2one('security.premise', string='Premise', required=True, tracking=True)
    client_id = fields.Many2one(related='premise_id.client_id', string='Client', store=True)

    # Status
    state = fields.Selection([
        ('allowed', 'Allowed to Stay'),
        ('not_allowed', 'Not Allowed to Stay'),
        ('warning', 'Warning Issued')
    ], string='Status', required=True, tracking=True)

    reason = fields.Text(string='Reason/Notes', required=True)
    action_taken = fields.Text(string='Action Taken')

    # Gate pass relation
    gate_pass_id = fields.Many2one('security.gate.pass', string='Related Gate Pass', tracking=True)
    has_valid_pass = fields.Boolean(string='Has Valid Pass', default=False, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('security.close.check') or _('New')
        return super().create(vals_list)

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
        if self.vehicle_id:
            # Check if vehicle has active gate pass
            valid_pass = self.env['security.gate.pass'].search([
                ('vehicle_id', '=', self.vehicle_id.id),
                ('state', '=', 'active'),
                ('end_date', '>=', fields.Date.today())
            ], limit=1)

            if valid_pass:
                self.gate_pass_id = valid_pass.id
                self.has_valid_pass = True
            else:
                self.gate_pass_id = False
                self.has_valid_pass = False
