from odoo import fields, models, api
from .qr_generator import generateQrCode
from odoo.http import request
from datetime import datetime


class HrActionLeaveReturn(models.Model):
    _name = 'hr.action.leave.return'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Action Leave Return'
    _rec_name = 'employee_id'

    def generate_barcode(self):
        return str(int(datetime.now().timestamp()))

    employee_id = fields.Many2one('hr.employee', required=True)
    image_1920 = fields.Image(related='employee_id.image_1920', store=True)
    barcode = fields.Char(default=generate_barcode)
    job_title = fields.Char(related='employee_id.job_title', store=True)
    employee_barcode = fields.Char(related='employee_id.barcode', store=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    last_leave_id = fields.Many2one('hr.leave', compute='compute_last_leave_dates', store=True)
    last_leave_from = fields.Date(compute='compute_last_leave_dates', store=True)
    last_leave_to = fields.Date(compute='compute_last_leave_dates', store=True)
    leave_return_date = fields.Date(compute='compute_last_leave_dates', store=True)
    start_work_date = fields.Date()
    leave_request_days = fields.Integer(compute='compute_last_leave_dates', store=True)
    actual_leave_days = fields.Integer(compute='compute_actual_leave_days', store=True)
    late_days = fields.Integer(compute='compute_late_days', store=True)
    late_fees = fields.Float()
    notes = fields.Text()
    state = fields.Selection(selection=[
        ('draft', 'Draft'), ('submit', 'Submitted'), ('approved', 'Approved'),
    ], default='draft')
    qr_image = fields.Binary("QR Code", compute='_generate_qr_code')
    qr_url = fields.Char("QR Code", compute='_generate_qr_code')
    active = fields.Boolean(default=True)

    def button_print_report(self):
        return self.env.ref('care_hr.action_leave_return_report').report_action(self)

    def button_print_report_header(self):
        return self.env.ref('care_hr.action_leave_return_header_report').report_action(self)

    @api.depends('employee_id')
    def compute_last_leave_dates(self):
        for rec in self:
            rec.last_leave_id = False
            rec.last_leave_from = False
            rec.last_leave_to = False
            rec.leave_request_days = False
            if rec.employee_id:
                all_leaves = self.env['hr.leave'].search([('employee_id', '=', rec.employee_id.id)]).sorted(lambda x: x.request_date_from, reverse=True)
                if all_leaves:
                    rec.last_leave_id = all_leaves[0].id
                    rec.last_leave_from = all_leaves[0].request_date_from
                    rec.last_leave_to = all_leaves[0].request_date_to
                    rec.leave_return_date = all_leaves[0].request_date_to
                    rec.leave_request_days = all_leaves[0].number_of_days

    @api.depends('start_work_date', 'last_leave_from')
    def compute_actual_leave_days(self):
        for rec in self:
            rec.actual_leave_days = 0
            if rec.last_leave_from and rec.start_work_date:
                if rec.last_leave_from < rec.start_work_date:
                    rec.actual_leave_days = (rec.start_work_date - rec.last_leave_from).days

    @api.depends('leave_return_date', 'start_work_date')
    def compute_late_days(self):
        for rec in self:
            rec.late_days = 0
            if rec.leave_return_date and rec.start_work_date:
                if rec.leave_return_date < rec.start_work_date:
                    rec.late_days = (rec.start_work_date - rec.leave_return_date).days

    def button_submit(self):
        self.state = 'submit'
        self.barcode = str(int(datetime.now().timestamp()))

    def button_approve(self):
        self.state = 'approved'
        if self.start_work_date and self.leave_return_date:
            if self.start_work_date < self.leave_return_date:
                original_date = self.last_leave_id.request_date_to
                holiday = self.last_leave_id
                holiday.write({
                    'original_return_date': original_date,
                    'request_date_to': self.start_work_date,
                    'number_of_days': self.actual_leave_days
                })

    def _generate_qr_code(self):
        for rec in self:
            qr_info = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            action_id = self.env.ref('care_hr.leave_return_action').id
            menu_id = self.env.ref('care_hr.leave_return_menu').id
            qr_info += '/web#id=%s&action=%s&model=%s&view_type=form&cids=&menu_id=%s' % (rec.id, action_id, 'hr.action.leave.return', menu_id)
            rec.qr_url = qr_info
            rec.qr_image = generateQrCode.generate_qr_code(qr_info)
