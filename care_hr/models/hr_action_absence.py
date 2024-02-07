from odoo import fields, models, api
from .qr_generator import generateQrCode
from odoo.http import request
from datetime import datetime


class HrActionAbsence(models.Model):
    _name = 'hr.action.absence'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'
    _description = 'Hr Action Absence'

    def generate_barcode(self):
        return str(int(datetime.now().timestamp()))

    employee_id = fields.Many2one('hr.employee', required=True)
    image_1920 = fields.Image(related='employee_id.image_1920', store=True)
    job_title = fields.Char(related='employee_id.job_title', store=True)
    civil_code = fields.Char(related='employee_id.civil_code', store=True)
    employee_barcode = fields.Char(related='employee_id.barcode', store=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    last_work_date = fields.Date(compute='compute_last_work_date', store=True)
    absence_reason = fields.Text(required=True)
    work_location = fields.Char()
    state = fields.Selection(selection=[
        ('draft', 'Draft'), ('submit', 'Submitted'), ('approved', 'Approved'),
    ], default='draft')

    barcode = fields.Char(default=generate_barcode)
    qr_image = fields.Binary("QR Code", compute='_generate_qr_code')
    qr_url = fields.Char("QR Code", compute='_generate_qr_code')
    active = fields.Boolean(default=True)

    def button_print_report(self):
        return self.env.ref('care_hr.action_absence_report').report_action(self)

    def button_print_report_header(self):
        return self.env.ref('care_hr.action_absence_header_report').report_action(self)

    @api.depends('employee_id')
    def compute_last_work_date(self):
        for rec in self:
            rec.last_work_date = False
            if rec.employee_id:
                all_attendance = self.env['hr.attendance'].search([('employee_id', '=', rec.employee_id.id)]).sorted(lambda x: x.check_in, reverse=True)
                if all_attendance:
                    rec.last_work_date = all_attendance[0].check_in.date()

    def button_submit(self):
        self.state = 'submit'
        # self.barcode = str(int(datetime.now().timestamp()))

    def button_approve(self):
        self.state = 'approved'

    def _generate_qr_code(self):
        for rec in self:
            qr_info = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            action_id = self.env.ref('care_hr.absence_view_form').id
            menu_id = self.env.ref('care_hr.absence_menu').id
            qr_info += '/web#id=%s&action=%s&model=%s&view_type=form&cids=&menu_id=%s' % (rec.id, action_id, 'hr.action.absence', menu_id)
            rec.qr_url = qr_info
            rec.qr_image = generateQrCode.generate_qr_code(qr_info)
