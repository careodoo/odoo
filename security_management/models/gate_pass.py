from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,UserError
import random
import string
from datetime import datetime, timedelta
import qrcode
import base64
from io import BytesIO


class SecurityGatePass(models.Model):
    _inherit = 'security.gate.pass'
    _description = 'Security Gate Pass'
    _order = 'create_date desc'

    name = fields.Char(string='Pass Number', readonly=True, copy=False)
    visitor_id = fields.Many2one('res.partner', string='Visitor', required=True, tracking=True)
    visitor_name = fields.Char(related='visitor_id.name', string='Visitor Name', readonly=True, store=True)
    visitor_phone = fields.Char(related='visitor_id.phone', string='Visitor Phone', readonly=True)
    visitor_email = fields.Char(related='visitor_id.email', string='Visitor Email', readonly=True)
    visitor_company = fields.Char(related='visitor_id.company_name', string='Visitor Company', readonly=True)
    client_id = fields.Many2one('security.client', string='Client', required=True, tracking=True)
    premise_id = fields.Many2one('security.premise', string='Premise', required=True, tracking=True,
                                domain="[('client_id', '=', client_id or False)]")

    # Visit details
    purpose = fields.Text(string='Purpose of Visit', required=True)
    valid_from = fields.Datetime(string='Valid From', required=True, default=fields.Datetime.now)
    valid_until = fields.Datetime(string='Valid Until', required=True)
    visit_date = fields.Date(string='Visit Date', compute='_compute_visit_date', store=True)
    is_recurring = fields.Boolean(string='Recurring Visit', default=False)
    recurring_days = fields.Many2many('security.weekday', string='Recurring Days')

    # Pass type
    pass_type = fields.Selection([
        ('personal', 'Personal'),
        ('vehicle', 'Vehicle')
    ], string='Pass Type', required=True, default='personal', tracking=True)

    # Host details
    host_id = fields.Many2one('hr.employee', string='Host', tracking=True)
    contact_id = fields.Many2one('security.contact', string='Contact Person', tracking=True,
                               domain="[('client_id', '=', client_id or False)]")

    # Vehicle details
    vehicle_id = fields.Many2one('security.vehicle', string='Vehicle')
    license_plate = fields.Char(string='License Plate')

    # Access details
    access_areas = fields.Many2many('security.access.area', string='Access Areas')
    require_escort = fields.Boolean(string='Requires Escort', default=False)
    escort_id = fields.Many2one('hr.employee', string='Escort')

    # Status and tracking
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('valid', 'Valid'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True)
    approved_date = fields.Datetime(string='Approval Date', readonly=True)

    # QR code and barcode for verification
    qr_code = fields.Binary(string='QR Code', readonly=True, copy=False, attachment=True)
    qr_code_text = fields.Char(string='QR Code Text', readonly=True, copy=False)
    barcode = fields.Char(string='Barcode', readonly=True, copy=False)

    # Visit records
    visit_record_ids = fields.One2many('security.visit.record', 'gate_pass_id', string='Visit Records')
    visit_count = fields.Integer(compute='_compute_visit_count', string='Visit Count')
    visit_log_ids = fields.One2many('security.visit.log', 'gate_pass_id', string='Visit Logs')

    # Computed fields
    days_valid = fields.Integer(compute='_compute_days_valid', string='Days Valid')
    person_count = fields.Integer(compute='_compute_person_count', string='Person Count', store=True)
    days_validity = fields.Integer(compute='_compute_days_validity', string='Days Validity', store=True)
    expected_arrival = fields.Datetime(string='Expected Arrival', compute='_compute_visit_date', store=True)
    expected_departure = fields.Datetime(string='Expected Departure', compute='_compute_visit_date', store=True)
    items_carried = fields.Many2many('product.product', string='Items Carried')
    checked_in = fields.Boolean(string='Checked In', default=False)
    checked_out = fields.Boolean(string='Checked Out', default=False)
    check_in_time = fields.Datetime(string='Check In Time', readonly=1, invisible=[('check_in_time', '=', False)])
    check_out_time = fields.Datetime(string='Check Out Time', readonly=1, invisible=[('check_out_time', '=', False)])
    approver_id = fields.Many2one('res.users', string='Approver', readonly=1, invisible=[('approver_id', '=', False)])
    approval_date = fields.Datetime(string='Approval Date', readonly=1, invisible=[('approval_date', '=', False)])
    rejection_reason = fields.Text(string='Rejection Reason', invisible=[('state', '!=', 'rejected')])
    notes = fields.Text(string='Notes')
    image_ids = fields.Many2many('ir.attachment', string='Images')

    @api.depends('valid_from', 'valid_until')
    def _compute_days_valid(self):
        for gate_pass in self:
            if gate_pass.valid_from and gate_pass.valid_until:
                delta = gate_pass.valid_until - gate_pass.valid_from
                gate_pass.days_valid = delta.days
            else:
                gate_pass.days_valid = 0

    @api.depends('visit_record_ids')
    def _compute_visit_count(self):
        for gate_pass in self:
            gate_pass.visit_count = len(gate_pass.visit_record_ids)

    @api.depends('valid_from', 'valid_until')
    def _compute_visit_date(self):
        """Compute the visit date based on the valid_from datetime"""
        for record in self:
            if record.valid_from:
                record.visit_date = record.valid_from.date()
                record.expected_arrival = record.valid_from
                record.expected_departure = record.valid_until
            else:
                record.visit_date = False
                record.expected_arrival = False
                record.expected_departure = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('security.gate.pass')

            # Generate QR code text
            if not vals.get('qr_code_text'):
                vals['qr_code_text'] = self._generate_unique_code('qrcode')

            # Generate barcode
            if not vals.get('barcode'):
                vals['barcode'] = self._generate_unique_code('barcode')

            # Generate QR code image
            if not vals.get('qr_code') and vals.get('qr_code_text'):
                qr_code_data = vals.get('qr_code_text')
                vals['qr_code'] = self._generate_qr_code_image(qr_code_data)

        return super().create(vals_list)

    def _generate_unique_code(self, code_type):
        """Generate a unique code for barcode or QR code"""
        if code_type == 'barcode':
            # Generate EAN-13 ISBN compatible barcode
            # ISBN EAN-13 starts with 978 or 979, followed by 9 digits, and a checksum
            prefix = '978'  # Standard ISBN prefix

            # Generate 9 random digits
            chars = string.digits
            random_digits = ''.join(random.choice(chars) for _ in range(9))

            # Combine prefix and random digits (12 digits total)
            code_without_checksum = prefix + random_digits

            # Calculate EAN-13 checksum
            total = 0
            for i, digit in enumerate(code_without_checksum):
                weight = 1 if i % 2 == 0 else 3
                total += int(digit) * weight
            checksum = (10 - (total % 10)) % 10

            # Complete EAN-13 code
            code = code_without_checksum + str(checksum)
        else:
            # QR code generation remains the same
            prefix = 'QRPASS-'
            chars = string.ascii_uppercase + string.digits
            code = prefix + ''.join(random.choice(chars) for _ in range(8))

        # Check if code exists
        existing_domain = [('barcode', '=', code)] if code_type == 'barcode' else [('qr_code_text', '=', code)]
        while self.search_count(existing_domain):
            if code_type == 'barcode':
                # Regenerate EAN-13 barcode
                random_digits = ''.join(random.choice(string.digits) for _ in range(9))
                code_without_checksum = prefix + random_digits

                # Recalculate checksum
                total = 0
                for i, digit in enumerate(code_without_checksum):
                    weight = 1 if i % 2 == 0 else 3
                    total += int(digit) * weight
                checksum = (10 - (total % 10)) % 10

                code = code_without_checksum + str(checksum)
            else:
                code = prefix + ''.join(random.choice(chars) for _ in range(8))

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
        qr_image = base64.b64encode(buffer.getvalue())

        return qr_image

    @api.constrains('valid_from', 'valid_until')
    def _check_dates(self):
        for record in self:
            if record.valid_from and record.valid_until:
                if record.valid_from > record.valid_until:
                    raise ValidationError(_("End date must be after start date"))

    def action_submit(self):
        """Submit gate pass for approval"""
        self.write({'state': 'pending'})

        # Create activity for security manager
        managers = self.env.ref('security_management.group_security_manager', False)
        if managers:
            for manager in managers.users:
                self.env['mail.activity'].create({
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'summary': _('Gate Pass Approval'),
                    'note': _('Please review and approve the gate pass for %s') % self.visitor_id.display_name,
                    'res_model_id': self.env.ref('security_management.model_security_gate_pass', False).id,
                    'res_id': self.id,
                    'user_id': manager.id,
                })

    def action_approve(self):
        """Approve gate pass"""
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        })

        # Generate QR code if not already generated
        for record in self:
            if not record.qr_code:
                record.qr_code_text = record._generate_unique_code('qrcode')
                record.qr_code = record._generate_qr_code_image(record.qr_code_text)

            if not record.barcode:
                record.barcode = record._generate_unique_code('barcode')

        # If valid from date is today or in the past, set to valid
        if self.valid_from <= fields.Datetime.now():
            self.write({'state': 'valid'})

        # Close any related activities
        activities = self.env['mail.activity'].search([
            ('res_id', '=', self.id),
            ('res_model', '=', 'security.gate.pass'),
            ('activity_type_id.category', '=', 'default')
        ])
        if activities:
            for activity in activities:
                activity._action_done(feedback=_("Approved by %s") % self.env.user.name)

        # Send email notification to visitor if email is available
        if self.visitor_id.email:
            template = self.env.ref('security_management.email_template_gate_pass', False)
            if template:
                template.send_mail(self.id, force_send=True)

    def action_reject(self):
        """Reject gate pass"""
        self.write({'state': 'cancelled'})

        # Close any related activities
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'security.gate.pass'),
            ('res_id', '=', self.id),
            ('summary', '=', 'Gate Pass Approval')
        ])
        if activities:
            for activity in activities:
                activity._action_done(feedback=_("Rejected by %s") % self.env.user.name)

        # Send email notification to visitor if email is available
        if self.visitor_id.email:
            template = self.env.ref('security_management.email_template_gate_pass_rejected', False)
            if template:
                template.send_mail(self.id, force_send=True)

    def action_cancel(self):
        """Cancel gate pass"""
        self.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        """Reset to draft"""
        self.write({'state': 'draft'})

    def action_view_visits(self):
        """View visit records"""
        self.ensure_one()
        return {
            'name': _('Visit Records'),
            'view_mode': 'tree,form',
            'res_model': 'security.visit.record',
            'domain': [('gate_pass_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_gate_pass_id': self.id},
        }

    def action_view_visitor(self):
        """View visitor details"""
        self.ensure_one()
        if not self.visitor_id:
            return

        return {
            'name': _('Visitor'),
            'view_mode': 'form',
            'res_model': 'res.partner',
            'res_id': self.visitor_id.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    def action_generate_qr_code(self):
        """Generate or regenerate QR code for the gate pass"""
        self.ensure_one()
        if self.state != 'approved':
            raise ValidationError(_("QR code can only be generated for approved gate passes"))

        # Generate a new unique QR code
        self.qr_code_text = self._generate_unique_code('qrcode')
        self.qr_code = self._generate_qr_code_image(self.qr_code_text)

        # Show success message
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('QR Code Generated'),
                'message': _('QR code has been generated successfully.'),
                'sticky': False,
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def action_check_in(self):
        """Check in a visitor with a gate pass"""
        self.ensure_one()

        # Validate state
        if self.state not in ['approved', 'valid']:
            raise UserError(_("Cannot check in with an invalid gate pass."))

        # Check if already checked in
        if self.checked_in and not self.checked_out:
            raise UserError(_("Visitor is already checked in."))

        # Create visit log entry
        self.env['security.visit.log'].with_context(company_id=self.env.company.id).create({
            'gate_pass_id': self.id,
            'event_type': 'check_in',
            'event_time': fields.Datetime.now(),
            'note': _("Checked in via scanner")
        })

        # Create visit record
        visit_vals = {
            'gate_pass_id': self.id,
            'visit_date': fields.Date.today(),
            'check_in_time': fields.Datetime.now(),
            'purpose': self.purpose,
            'state': 'checked_in',
        }

        self.env['security.visit.record'].with_context(company_id=self.env.company.id).create(visit_vals)

        # Update gate pass
        self.write({
            'checked_in': True,
            'check_in_time': fields.Datetime.now(),
            'state': 'valid'
        })

        return True

    def action_check_out(self):
        """Check out a visitor with a gate pass"""
        self.ensure_one()

        # Create visit log entry
        self.env['security.visit.log'].with_context(company_id=self.env.company.id).create({
            'gate_pass_id': self.id,
            'event_type': 'check_out',
            'event_time': fields.Datetime.now(),
            'note': _("Checked out via scanner")
        })

        # Update the latest visit record
        visit_record = self.env['security.visit.record'].search([
            ('gate_pass_id', '=', self.id),
            ('state', '=', 'checked_in')
        ], limit=1, order='check_in_time desc')

        if visit_record:
            visit_record.with_context(company_id=self.env.company.id).write({
                'check_out_time': fields.Datetime.now(),
                'state': 'checked_out'
            })

        # Update gate pass
        self.write({
            'checked_out': True,
            'check_out_time': fields.Datetime.now()
        })

        return True

    def action_print_gate_pass(self):
        """Print gate pass"""
        self.ensure_one()
        return self.env.ref('security_management.action_report_gate_pass', False).report_action(self)

    def regenerate_qr_code(self):
        """Regenerate QR code for the gate pass"""
        self.ensure_one()

        if self.state not in ['approved', 'valid']:
            raise ValidationError(_("QR code can only be generated for approved gate passes"))

        # Generate a new unique QR code
        self.qr_code_text = self._generate_unique_code('qrcode')
        self.qr_code = self._generate_qr_code_image(self.qr_code_text)

        # Show success message
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('QR code has been regenerated successfully.'),
                'sticky': False,
                'type': 'success',
            }
        }

    @api.model
    def _cron_check_expired_passes(self):
        """Cron job to check and mark expired gate passes"""
        now = fields.Datetime.now()
        expired_passes = self.search([
            ('state', '=', 'valid'),
            ('valid_until', '<', now)
        ])
        expired_passes.write({'state': 'expired'})

        # Create new passes for recurring visits
        tomorrow = fields.Date.today() + timedelta(days=1)
        weekday = tomorrow.weekday()  # 0 is Monday, 6 is Sunday

        recurring_passes = self.search([
            ('is_recurring', '=', True),
            ('state', 'in', ['valid', 'expired']),
            ('recurring_days', 'in', [weekday + 1])  # +1 because our model uses 1-7 for weekdays
        ])

        for pass_record in recurring_passes:
            # Check if there's already a pass for tomorrow
            existing_pass = self.search([
                ('visitor_id', '=', pass_record.visitor_id.id),
                ('premise_id', '=', pass_record.premise_id.id),
                ('valid_from', '>=', datetime.combine(tomorrow, datetime.min.time())),
                ('valid_from', '<', datetime.combine(tomorrow + timedelta(days=1), datetime.min.time()))
            ], limit=1)

            if not existing_pass:
                # Create new pass for tomorrow
                new_pass = pass_record.copy({
                    'valid_from': datetime.combine(tomorrow, datetime.min.time()) + timedelta(hours=8),  # 8 AM
                    'valid_until': datetime.combine(tomorrow, datetime.min.time()) + timedelta(hours=18),  # 6 PM
                    'state': 'approved'
                })
                new_pass.message_post(body=_("Automatically created from recurring pass %s") % pass_record.name)

    @api.depends('person_ids')
    def _compute_person_count(self):
        for gate_pass in self:
            gate_pass.person_count = len(gate_pass.person_ids)

    @api.depends('valid_from', 'valid_until')
    def _compute_days_validity(self):
        for gate_pass in self:
            if gate_pass.valid_from and gate_pass.valid_until:
                delta = gate_pass.valid_until - gate_pass.valid_from
                gate_pass.days_validity = delta.days
            else:
                gate_pass.days_validity = 0


class SecurityWeekday(models.Model):
    _name = 'security.weekday'
    _description = 'Weekday for Recurring Visits'
    _order = 'sequence'

    name = fields.Char(string='Day Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    code = fields.Char(string='Day Code', size=3, required=True)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'Day code must be unique!')
    ]


class SecurityAccessArea(models.Model):
    _name = 'security.access.area'
    _description = 'Security Access Area'
    _order = 'name'

    name = fields.Char(string='Area Name', required=True)
    code = fields.Char(string='Area Code', required=True)
    description = fields.Text(string='Description')
    restricted = fields.Boolean(string='Restricted Area', default=False,
                              help="If checked, this area requires special authorization")
    manager_id = fields.Many2one('hr.employee', string='Area Manager')
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'Area code must be unique!')
    ]


class SecurityVisitLog(models.Model):
    _name = 'security.visit.log'
    _description = 'Security Visit Log'
    _order = 'event_time desc'

    gate_pass_id = fields.Many2one('security.gate.pass', string='Gate Pass', required=True, ondelete='cascade')
    event_type = fields.Selection([
        ('check_in', 'Check In'),
        ('check_out', 'Check Out'),
        ('approval', 'Approval'),
        ('rejection', 'Rejection'),
        ('cancellation', 'Cancellation'),
        ('other', 'Other')
    ], string='Event Type', required=True)
    event_time = fields.Datetime(string='Event Time', default=fields.Datetime.now, required=True)
    recorded_by = fields.Many2one('res.users', string='Recorded By', default=lambda self: self.env.user.id, required=True)
    location_latitude = fields.Float(string='Latitude', digits=(16, 8))
    location_longitude = fields.Float(string='Longitude', digits=(16, 8))
    note = fields.Text(string='Note')
    image_ids = fields.Many2many('ir.attachment', string='Images')


class SecurityVisitRecord(models.Model):
    _name = 'security.visit.record'
    _description = 'Visit Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'check_in_time desc'

    name = fields.Char(string='Visit ID', readonly=True, copy=False)
    gate_pass_id = fields.Many2one('security.gate.pass', string='Gate Pass', required=True, ondelete='cascade')
    visitor_id = fields.Many2one(related='gate_pass_id.visitor_id', string='Visitor', store=True)
    client_id = fields.Many2one(related='gate_pass_id.client_id', string='Client', store=True)
    premise_id = fields.Many2one(related='gate_pass_id.premise_id', string='Premise', store=True)
    visit_date = fields.Date(string='Visit Date', default=fields.Date.today, tracking=True)

    # Contact information
    contact_name = fields.Char(string='Contact Name', store=True)
    contact_email = fields.Char(string='Contact Email', store=True)
    contact_phone = fields.Char(string='Contact Phone', store=True)
    contact_position = fields.Char(string='Contact Position', store=True)

    # Visit details
    visitor_count = fields.Integer(string='Visitor Count', default=1, tracking=True)
    accompanied_by = fields.Char(string='Accompanied By')
    floor_id = fields.Many2one('security.floor', string='Floor', tracking=True)
    unit_id = fields.Many2one('security.unit', string='Unit', tracking=True)
    notes = fields.Text(string='Notes')
    purpose = fields.Text(string='Purpose', required=True)

    check_in_time = fields.Datetime(string='Check In Time', required=True, default=fields.Datetime.now)
    check_out_time = fields.Datetime(string='Check Out Time')
    checked_in_by = fields.Many2one('res.users', string='Checked In By', default=lambda self: self.env.user.id)
    checked_out_by = fields.Many2one('res.users', string='Checked Out By')

    # Additional visit details
    vehicle_id = fields.Many2one(related='gate_pass_id.vehicle_id', string='Vehicle', store=True)
    license_plate = fields.Char(related='gate_pass_id.license_plate', string='License Plate', store=True)
    purpose = fields.Text(related='gate_pass_id.purpose', string='Purpose of Visit', store=True)

    # Items carried
    items_carried_in = fields.Text(string='Items Carried In')
    items_carried_out = fields.Text(string='Items Carried Out')

    # Visit status
    state = fields.Selection([
        ('planned', 'Planned'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='planned', tracking=True)

    def action_check_in(self):
        """Check in the visitor"""
        self.ensure_one()
        if self.state != 'planned':
            raise UserError(_("Only planned visits can be checked in"))

        self.write({
            'state': 'checked_in',
            'check_in_time': fields.Datetime.now(),
        })
        return True

    # Computed fields
    visit_duration = fields.Float(compute='_compute_visit_duration', string='Duration (Hours)', store=True)
    contact_name = fields.Char(string='Contact Name', store=True)
    contact_email = fields.Char(string='Contact Email', store=True)
    contact_phone = fields.Char(string='Contact Phone', store=True)

    @api.depends('check_in_time', 'check_out_time')
    def _compute_visit_duration(self):
        for record in self:
            if record.check_in_time and record.check_out_time:
                duration = (record.check_out_time - record.check_in_time).total_seconds() / 3600
                record.visit_duration = round(duration, 2)
            else:
                record.visit_duration = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('security.visit.record')
        return super().create(vals_list)

    def action_check_out(self):
        """Check out visitor"""
        self.ensure_one()
        if self.state != 'checked_in':
            raise UserError(_("Only checked in visits can be checked out"))

        self.write({
            'state': 'checked_out',
            'check_out_time': fields.Datetime.now(),
        })
        if self.check_out_time:
            raise ValidationError(_("Visitor already checked out"))

        return {
            'name': _('Check Out Visitor'),
            'view_mode': 'form',
            'res_model': 'security.visitor.checkout.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'default_visit_record_id': self.id},
        }

    def action_cancel(self):
        """Cancel visit"""
        self.ensure_one()
        if self.state in ['checked_in', 'checked_out']:
            raise UserError(_("Cannot cancel a visit that has already started"))
        self.write({
            'state': 'cancelled',
            'check_out_time': fields.Datetime.now(),
            'checked_out_by': self.env.user.id,
        })

class SecurityVehicle(models.Model):
    _name = 'security.vehicle'
    _description = 'Security Vehicle'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Vehicle Description', compute='_compute_name', store=True, tracking=True)
    license_plate = fields.Char(string='License Plate', required=True, tracking=True)
    vehicle_type = fields.Selection([
            ('car', 'Car'),
            ('truck', 'Truck'),
            ('van', 'Van'),
            ('motorcycle', 'Motorcycle'),
            ('other', 'Other')
        ], string='Vehicle Type', default='car', required=True, tracking=True)
    make = fields.Char(string='Make', tracking=True)
    model = fields.Char(string='Model', tracking=True)
    color = fields.Char(string='Color', tracking=True)
    year = fields.Char(string='Year', tracking=True)
    owner_id = fields.Many2one('res.partner', string='Owner', tracking=True)

    # Add the missing fields
    gate_pass_ids = fields.One2many('security.gate.pass', 'vehicle_id', string='Gate Passes')
    gate_pass_count = fields.Integer(compute='_compute_gate_pass_count', string='Gate Pass Count')
    close_check_ids = fields.One2many('security.close.check', 'vehicle_id', string='Close Checks')
    close_check_count = fields.Integer(compute='_compute_close_check_count', string='Close Check Count')

    _sql_constraints = [
            ('license_plate_uniq', 'UNIQUE(license_plate)', 'License plate must be unique!')
        ]

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

    def action_view_gate_passes(self):
        self.ensure_one()
        return {
            'name': _('Gate Passes'),
            'view_mode': 'tree,form',
            'res_model': 'security.gate.pass',
            'domain': [('vehicle_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_vehicle_id': self.id},
        }
