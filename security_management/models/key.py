from odoo import models, fields, api, _
import random
import string
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import qrcode
import base64
from io import BytesIO

class SecurityKeyHub(models.Model):
    _name = 'security.key.hub'
    _description = 'Key Hub'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Hub Name', required=True, tracking=True)
    code = fields.Char(string='Hub Code', required=True, tracking=True, copy=False)
    location = fields.Char(string='Location', required=True, tracking=True)
    premise_id = fields.Many2one('security.premise', string='Premise', required=True, tracking=True)
    client_id = fields.Many2one(related='premise_id.client_id', string='Client', store=True)
    responsible_id = fields.Many2one('hr.employee', string='Responsible Person', tracking=True)
    key_ids = fields.One2many('security.key', 'key_hub_id', string='Keys')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    # Computed fields
    key_count = fields.Integer(compute='_compute_key_count', string='Total Keys')
    available_key_count = fields.Integer(compute='_compute_available_key_count', string='Available Keys')
    checked_out_key_count = fields.Integer(compute='_compute_checked_out_key_count', string='Checked Out Keys')
    lost_key_count = fields.Integer(compute='_compute_lost_key_count', string='Lost Keys')

    _sql_constraints = [
        ('code_uniq', 'UNIQUE(code)', 'Hub Code must be unique!'),
    ]

    @api.depends('key_ids')
    def _compute_key_count(self):
        for hub in self:
            hub.key_count = len(hub.key_ids)

    @api.depends('key_ids', 'key_ids.state')
    def _compute_available_key_count(self):
        for hub in self:
            hub.available_key_count = len(hub.key_ids.filtered(lambda k: k.state == 'available'))

    @api.depends('key_ids', 'key_ids.state')
    def _compute_checked_out_key_count(self):
        for hub in self:
            hub.checked_out_key_count = len(hub.key_ids.filtered(lambda k: k.state == 'checked_out'))

    @api.depends('key_ids', 'key_ids.state')
    def _compute_lost_key_count(self):
        for hub in self:
            hub.lost_key_count = len(hub.key_ids.filtered(lambda k: k.state == 'lost'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code'):
                vals['code'] = self.env['ir.sequence'].next_by_code('security.key.hub')
        return super().create(vals_list)

    def action_view_keys(self):
        self.ensure_one()
        return {
            'name': _('Keys'),
            'view_mode': 'tree,form',
            'res_model': 'security.key',
            'domain': [('key_hub_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_key_hub_id': self.id},
        }

    def action_view_logs(self):
        self.ensure_one()
        return {
            'name': _('Key Logs'),
            'view_mode': 'tree,form',
            'res_model': 'security.key.log',
            'domain': [('key_id.key_hub_id', '=', self.id)],
            'type': 'ir.actions.act_window',
        }


class SecurityKey(models.Model):
    _name = 'security.key'
    _description = 'Security Key'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Key Name', required=True, tracking=True)
    door_number = fields.Char(string='Door Number', required=True, tracking=True)
    key_number = fields.Char(string='Key Number', required=True, tracking=True)
    key_type = fields.Selection([
        ('master', 'Master Key'),
        ('room', 'Room Key'),
        ('cabinet', 'Cabinet Key'),
        ('padlock', 'Padlock Key'),
        ('other', 'Other')
    ], string='Key Type', default='room', tracking=True)
    description = fields.Text(string='Description')
    barcode = fields.Char(string='Barcode', readonly=True, copy=False)
    qr_code = fields.Binary(string='QR Code', readonly=True, copy=False, attachment=True)
    qr_code_text = fields.Char(string='QR Code Text', readonly=True, copy=False)

    # Relations
    unit_id = fields.Many2one('security.unit', string='Unit', required=True, tracking=True)
    floor_id = fields.Many2one(related='unit_id.floor_id', string='Floor', store=True)
    premise_id = fields.Many2one(related='floor_id.premise_id', string='Premise', store=True)
    client_id = fields.Many2one(related='premise_id.client_id', string='Client', store=True)
    key_hub_id = fields.Many2one('security.key.hub', string='Key Hub', required=True, tracking=True)
    current_holder_id = fields.Many2one('hr.employee', string='Current Holder', tracking=True,
                                        help="Employee who currently has the key checked out")

    # Status fields
    state = fields.Selection([
        ('available', 'Available'),
        ('checked_out', 'Checked Out'),
        ('maintenance', 'Maintenance'),
        ('lost', 'Lost')
    ], string='Status', default='available', tracking=True)
    check_out_time = fields.Datetime(string='Last Check Out', readonly=True)
    expected_return_time = fields.Datetime(string='Expected Return', readonly=True)

    # Key logs
    log_ids = fields.One2many('security.key.log', 'key_id', string='Key Logs')
    log_count = fields.Integer(compute='_compute_log_count', string='Log Count')
    days_overdue = fields.Integer(compute='_compute_days_overdue', string='Days Overdue')

    @api.depends('log_ids')
    def _compute_log_count(self):
        for key in self:
            key.log_count = len(key.log_ids)

    @api.depends('expected_return_time', 'state')
    def _compute_days_overdue(self):
        now = fields.Datetime.now()
        for key in self:
            if key.state == 'checked_out' and key.expected_return_time and key.expected_return_time < now:
                delta = now - key.expected_return_time
                key.days_overdue = delta.days
            else:
                key.days_overdue = 0

    @api.model_create_multi
    def create(self, vals_list):
        """Override create method to generate sequence and codes"""
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('security.key') or _('New')

            if not vals.get('barcode'):
                vals['barcode'] = self._generate_unique_code('barcode')

            if not vals.get('qr_code_text'):
                vals['qr_code_text'] = self._generate_unique_code('qrcode')

            if not vals.get('qr_code') and vals.get('qr_code_text'):
                qr_code_data = vals.get('qr_code_text')
                vals['qr_code'] = self._generate_qr_code_image(qr_code_data)

        return super(SecurityKey, self).create(vals_list)

    def _generate_unique_code(self, code_type):
        """Generate a unique barcode or QR code"""
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

        # Check if code already exists
        existing_domain = [('barcode', '=', code)] if code_type == 'barcode' else [('qr_code_text', '=', code)]
        while self.search_count(existing_domain):
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
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

    def action_check_out(self):
        """Open wizard to check out the key"""
        self.ensure_one()
        if self.state != 'available':
            raise UserError(_("Only available keys can be checked out"))

        return {
            'name': _('Check Out Key'),
            'view_mode': 'form',
            'res_model': 'security.key.checkout.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'default_key_id': self.id},
        }

    def action_check_in(self):
        """Open wizard to check in the key"""
        self.ensure_one()
        if self.state != 'checked_out':
            raise UserError(_("Only checked out keys can be checked in"))

        return {
            'name': _('Check In Key'),
            'view_mode': 'form',
            'res_model': 'security.key.checkin.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'default_key_id': self.id},
        }

    def action_mark_lost(self):
        """Mark the key as lost"""
        self.ensure_one()
        if self.state == 'lost':
            raise UserError(_("Key is already marked as lost"))

        return {
            'name': _('Mark Key as Lost'),
            'view_mode': 'form',
            'res_model': 'security.key.lost.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'default_key_id': self.id},
        }

    def action_view_logs(self):
        self.ensure_one()
        return {
            'name': _('Key Logs'),
            'view_mode': 'tree,form',
            'res_model': 'security.key.log',
            'domain': [('key_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_key_id': self.id},
        }

    def action_generate_qr_code(self):
        """Generate QR Code for the key"""
        for record in self:
            record.qr_code_text = record._generate_unique_code('qrcode')
            record.qr_code = record._generate_qr_code_image(record.qr_code_text)

    def action_recover(self):
        """Recover a lost key"""
        self.ensure_one()
        if self.state != 'lost':
            raise UserError(_('Only lost keys can be recovered'))

        # Create a key log entry for the recovery
        self.env['security.key.log'].create({
            'key_id': self.id,
            'security_employee_id': self.env.user.employee_id.security_employee_id and self.env['security.employee'].search([('employee_id', '=', self.env.user.employee_id.id)], limit=1).id or self.env['security.employee'].search([], limit=1).id,
            'operation': 'found',
            'reason': _('Key recovered')
        })

        # Update the key state
        self.write({
            'state': 'available',
            'current_holder_id': False,
            'check_out_time': False,
            'expected_return_time': False
        })

        return {'type': 'ir.actions.act_window_close'}


class SecurityKeyLog(models.Model):
    _name = 'security.key.log'
    _description = 'Key Log'
    _order = 'timestamp desc'

    key_id = fields.Many2one('security.key', string='Key', required=True, ondelete='cascade')
    security_employee_id = fields.Many2one('security.employee', string='Employee', required=True)
    operation = fields.Selection([
        ('check_out', 'Check Out'),
        ('check_in', 'Check In'),
        ('lost', 'Marked Lost'),
        ('found', 'Found'),
        ('maintenance', 'Maintenance')
    ], string='Operation', required=True)
    timestamp = fields.Datetime(string='Timestamp', default=fields.Datetime.now, required=True)
    expected_return = fields.Datetime(string='Expected Return')
    reason = fields.Text(string='Reason/Notes')

    # Related fields for easy search
    key_hub_id = fields.Many2one(related='key_id.key_hub_id', string='Key Hub', store=True)
    unit_id = fields.Many2one(related='key_id.unit_id', string='Unit', store=True)
    premise_id = fields.Many2one(related='key_id.premise_id', string='Premise', store=True)
    client_id = fields.Many2one(related='key_id.client_id', string='Client', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        logs = super().create(vals_list)

        # Create activity notification for key return if expected return is set
        for log in logs:
            if log.operation == 'check_out' and log.expected_return:
                log.key_id.activity_schedule(
                    'security_management.mail_activity_key_return',
                    summary=_('Key Return Reminder'),
                    note=_('Key %s needs to be returned by %s') % (log.key_id.name, log.expected_return),
                    deadline=log.expected_return.date(),
                    user_id=log.security_employee_id.user_id.id or self.env.user.id
                )

        return logs


class SecurityKeyHistory(models.Model):
    _name = 'security.key.history'
    _description = 'Key History'
    _order = 'event_time desc'

    key_id = fields.Many2one('security.key', string='Key', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda self: self.env.user)
    event_type = fields.Selection([
        ('check_out', 'Check Out'),
        ('check_in', 'Check In'),
        ('lost', 'Marked Lost'),
        ('found', 'Found'),
        ('maintenance', 'Maintenance')
    ], string='Event Type', required=True)
    event_time = fields.Datetime(string='Event Time', default=fields.Datetime.now, required=True)
    location_latitude = fields.Float(string='Latitude', digits=(16, 8))
    location_longitude = fields.Float(string='Longitude', digits=(16, 8))
    note = fields.Text(string='Notes')
    image_ids = fields.Many2many('ir.attachment', string='Images')

    # Related fields for easy search
    key_hub_id = fields.Many2one(related='key_id.key_hub_id', string='Key Hub', store=True)
    unit_id = fields.Many2one(related='key_id.unit_id', string='Unit', store=True)
    premise_id = fields.Many2one(related='key_id.premise_id', string='Premise', store=True)
    client_id = fields.Many2one(related='key_id.client_id', string='Client', store=True)
