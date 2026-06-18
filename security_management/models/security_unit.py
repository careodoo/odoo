from odoo import models, fields, api, _
import random
import string
from odoo.exceptions import ValidationError
import qrcode
import base64
from io import BytesIO


class SecurityUnit(models.Model):
    _name = 'security.unit'
    _description = 'Premise Unit'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Unit Name', required=True, tracking=True)
    unit_number = fields.Char(string='Unit Number', required=True, tracking=True)
    floor_id = fields.Many2one('security.floor', string='Floor', required=True, tracking=True)
    premise_id = fields.Many2one(related='floor_id.premise_id', string='Premise', store=True)
    client_id = fields.Many2one(related='premise_id.client_id', string='Client', store=True)
    code = fields.Char(string='Unit Code', readonly=True, copy=False)
    barcode = fields.Char(string='Barcode', readonly=True, copy=False)
    qr_code = fields.Binary(string='QR Code', readonly=True, copy=False, attachment=True)
    qr_code_text = fields.Char(string='QR Code Text', readonly=True, copy=False)
    unit_type = fields.Selection([
        ('office', 'Office'),
        ('restaurant', 'Restaurant'),
        ('shop', 'Shop'),
        ('cafe', 'Cafe'),
        ('storage', 'Storage'),
        ('other', 'Other')
    ], string='Unit Type', default='other', required=True)
    description = fields.Text(string='Description')

    # Relations
    key_ids = fields.One2many('security.key', 'unit_id', string='Keys')
    patrol_point_ids = fields.One2many('security.patrol.point', 'unit_id', string='Patrol Points')

    # Computed fields
    key_count = fields.Integer(compute='_compute_key_count', string='Key Count')
    patrol_point_count = fields.Integer(compute='_compute_patrol_point_count', string='Patrol Points')

    # Company field with proper security pattern
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        groups='base.group_multi_company',
        help='Company this record belongs to'
    )

    @api.depends('key_ids')
    def _compute_key_count(self):
        for unit in self:
            unit.key_count = len(unit.key_ids)

    @api.depends('patrol_point_ids')
    def _compute_patrol_point_count(self):
        for unit in self:
            unit.patrol_point_count = len(unit.patrol_point_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code'):
                vals['code'] = self.env['ir.sequence'].next_by_code('security.unit') or _('New')

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
        prefix = 'UNIT-' if code_type == 'barcode' else 'QRUNIT-'

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

    def action_view_keys(self):
        self.ensure_one()
        return {
            'name': _('Keys'),
            'view_mode': 'tree,form',
            'res_model': 'security.key',
            'domain': [('unit_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_unit_id': self.id},
        }

    def action_generate_qr_code(self):
        """Generate QR Code for the unit"""
        for record in self:
            record.qr_code_text = record._generate_unique_code('qrcode')
            record.qr_code = record._generate_qr_code_image(record.qr_code_text)
