from odoo import fields, models, api
from odoo.exceptions import ValidationError
from .qr_generator import generateQrCode
from odoo.http import request
from datetime import datetime


class PermissionRequest(models.Model):
    _name = 'permission.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Permission Request'

    def generate_barcode(self):
        return str(int(datetime.now().timestamp()))

    employee_id = fields.Many2one('hr.employee', required=True)
    employee_barcode = fields.Char(related='employee_id.barcode', store=True, string='Employee ID')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    position = fields.Char(related='employee_id.job_title', store=True)
    type = fields.Selection(selection=[
        ('official', 'Official'), ('personal', 'Personal')
    ], required=True)
    permission_from = fields.Datetime(required=True)
    permission_to = fields.Datetime(required=True)
    reason = fields.Text(required=True)
    barcode = fields.Char(default=generate_barcode)
    qr_image = fields.Binary("QR Code", compute='_generate_qr_code')
    qr_url = fields.Char("QR Code", compute='_generate_qr_code')

    def _generate_qr_code(self):
        for rec in self:
            qr_info = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            action_id = self.env.ref('permission_request.permission_request_view_form').id
            menu_id = self.env.ref('permission_request.permission_request_menu').id
            qr_info += '/web#id=%s&action=%s&model=%s&view_type=form&cids=&menu_id=%s' % (rec.id, action_id, 'permission.request', menu_id)
            rec.qr_url = qr_info
            rec.qr_image = generateQrCode.generate_qr_code(qr_info)

    @api.constrains('permission_from', 'permission_to')
    def check_dates(self):
        for rec in self:
            if rec.permission_from > rec.permission_to:
                raise ValidationError("From must be earlier than To!")
