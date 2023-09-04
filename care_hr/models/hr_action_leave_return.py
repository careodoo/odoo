from odoo import fields, models, api
from .qr_generator import generateQrCode
from odoo.http import request
from datetime import datetime


class HrActionLeaveReturn(models.Model):
    _name = 'hr.action.leave.return'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Action Leave Return'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', required=True)
    job_title = fields.Char(related='employee_id.job_title', store=True)
    employee_barcode = fields.Char(related='employee_id.barcode', store=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    last_leave_from = fields.Date()
    last_leave_to = fields.Date()
    leave_return_date = fields.Date()
    start_work_date = fields.Date()
    leave_request_days = fields.Integer()
    actual_leave_days = fields.Integer()
    late_days = fields.Integer()
    late_fees = fields.Float()
    notes = fields.Text()
    state = fields.Selection(selection=[
        ('draft', 'Draft'), ('submit', 'Submitted'), ('approved', 'Approved'),
    ], default='draft')
    barcode = fields.Char()
    qr_image = fields.Binary("QR Code", compute='_generate_qr_code')
    qr_url = fields.Char("QR Code", compute='_generate_qr_code')

    def button_submit(self):
        self.state = 'submit'
        self.barcode = str(int(datetime.now().timestamp()))

    def button_approve(self):
        self.state = 'approved'

    def _generate_qr_code(self):
        for rec in self:
            qr_info = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            action_id = self.env.ref('care_hr.leave_return_view_form').id
            menu_id = self.env.ref('care_hr.leave_return_menu').id
            qr_info += '/web#id=%s&action=%s&model=%s&view_type=form&cids=&menu_id=%s' % (rec.id, action_id, 'hr.action.leave.return', menu_id)
            rec.qr_url = qr_info
            rec.qr_image = generateQrCode.generate_qr_code(qr_info)
