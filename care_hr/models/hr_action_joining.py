from odoo import fields, models, api
from .qr_generator import generateQrCode
from odoo.http import request
from datetime import datetime


class HrActionJoining(models.Model):
    _name = 'hr.action.joining'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Action Joining'
    _rec_name = 'employee_id'

    def generate_barcode(self):
        return str(int(datetime.now().timestamp()))

    employee_id = fields.Many2one('hr.employee', required=True)
    image_1920 = fields.Image(related='employee_id.image_1920', store=True)
    barcode = fields.Char(default=generate_barcode)
    qr_image = fields.Binary("QR Code", compute='_generate_qr_code')
    qr_url = fields.Char("QR Code", compute='_generate_qr_code')
    job_title = fields.Char(related='employee_id.job_title', store=True)
    employee_barcode = fields.Char(related='employee_id.barcode', store=True)
    join_date = fields.Date(required=True)
    delay = fields.Integer()
    salary_date = fields.Date()
    department_id = fields.Many2one('hr.department', related='employee_id.department_id')
    state = fields.Selection(selection=[
        ('draft', 'Draft'), ('submit', 'Submitted'), ('approved', 'Approved'),
    ], default='draft')
    active = fields.Boolean(default=True)

    def button_print_report(self):
        return self.env.ref('care_hr.action_joining_report').report_action(self)

    def button_print_report_header(self):
        return self.env.ref('care_hr.action_joining_header_report').report_action(self)

    def button_submit(self):
        self.state = 'submit'
        self.barcode = str(int(datetime.now().timestamp()))

    def button_approve(self):
        self.state = 'approved'

    def _generate_qr_code(self):
        for rec in self:
            qr_info = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            action_id = self.env.ref('care_hr.joining_view_form').id
            menu_id = self.env.ref('care_hr.joining_menu').id
            qr_info += '/web#id=%s&action=%s&model=%s&view_type=form&cids=&menu_id=%s' % (rec.id, action_id, 'hr.action.joining', menu_id)
            rec.qr_url = qr_info
            rec.qr_image = generateQrCode.generate_qr_code(qr_info)
