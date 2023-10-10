from odoo import fields, models, api
from datetime import datetime
from .qr_generator import generateQrCode
from odoo.http import request


class Leave(models.Model):
    _inherit = 'hr.leave'

    def generate_barcode(self):
        return str(int(datetime.now().timestamp()))

    barcode = fields.Char(default=generate_barcode)
    qr_image = fields.Binary("QR Code", compute='_generate_qr_code')
    qr_url = fields.Char("QR Code", compute='_generate_qr_code')

    def _generate_qr_code(self):
        for rec in self:
            qr_info = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            action_id = self.env.ref('hr_holidays.hr_leave_view_form_manager').id
            menu_id = self.env.ref('hr_holidays.menu_open_department_leave_approve').id
            qr_info += '/web#id=%s&action=%s&model=%s&view_type=form&cids=&menu_id=%s' % (rec.id, action_id, 'hr.leave', menu_id)
            rec.qr_url = qr_info
            rec.qr_image = generateQrCode.generate_qr_code(qr_info)
