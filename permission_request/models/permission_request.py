from odoo import fields, models, api
from odoo.exceptions import ValidationError
from .qr_generator import generateQrCode
from odoo.http import request
from datetime import datetime
from dateutil.relativedelta import relativedelta


class PermissionRequest(models.Model):
    _name = 'permission.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Permission Request'

    def generate_barcode(self):
        return str(int(datetime.now().timestamp()))

    employee_id = fields.Many2one('hr.employee', required=True)
    employee_barcode = fields.Char(related='employee_id.barcode', store=True, string='Employee ID')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    approver_ids = fields.Many2many('res.users', compute='compute_approver_ids', store=True)
    position = fields.Char(related='employee_id.job_title', store=True)
    type = fields.Selection(selection=[
        ('official', 'Official'), ('personal', 'Personal')
    ], required=True)
    permission_from = fields.Datetime(required=True)
    permission_hours = fields.Integer(required=True)
    permission_to = fields.Datetime(compute='compute_permission_to', store=True)
    reason = fields.Text(required=True)
    barcode = fields.Char(default=generate_barcode)
    qr_image = fields.Binary("QR Code", compute='_generate_qr_code')
    qr_url = fields.Char("QR Code", compute='_generate_qr_code')
    active = fields.Boolean(default=True)
    total_hours = fields.Integer(compute='compute_hours', store=True, string='Total Allocated H/M')
    total_extra_hours = fields.Integer(compute='compute_hours', store=True, string='Total Extra H/M')
    used_hours = fields.Integer(compute='compute_hours', store=True, string='Used H/M')
    remaining_hours = fields.Integer(compute='compute_hours', store=True, string='Remaining H/M')
    need_more_hours = fields.Boolean(compute='compute_need_more_hours', store=True)
    extra_hour_ids = fields.One2many('permission.request.extra.hour', 'permission_request_id')
    extra_hour_count = fields.Integer(compute='compute_extra_hour_count', store=True)
    state = fields.Selection(selection=[
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'), ('rejected', 'Rejected')
    ], default='draft')

    @api.constrains('permission_hours')
    def check_permission_hours(self):
        for rec in self:
            if rec.permission_hours <= 0:
                raise ValidationError("Hours should be positive!")
            hours = self.env['ir.config_parameter'].sudo().get_param('permission_request.permission_request_hours') or False
            if hours:
                if int(hours) < rec.permission_hours:
                    raise ValidationError("Hours should not exceed total allocated hours!")

    @api.depends('permission_from', 'permission_hours')
    def compute_permission_to(self):
        for rec in self:
            rec.permission_to = 0
            if rec.permission_from and rec.permission_hours:
                rec.permission_to = rec.permission_from + relativedelta(hours=rec.permission_hours)

    @api.depends('employee_id', 'permission_from', 'permission_hours', 'state', 'extra_hour_ids.state')
    def compute_hours(self):
        for rec in self:
            rec.total_hours = 0
            rec.total_extra_hours = 0
            rec.used_hours = 0
            rec.remaining_hours = 0
            if rec.employee_id and rec.permission_from:
                hours = self.env['ir.config_parameter'].sudo().get_param('permission_request.permission_request_hours') or False
                if hours:
                    rec.total_hours = int(hours)
                    rec.total_extra_hours = sum(self.env['permission.request.extra.hour'].search([('employee_id', '=', rec.employee_id.id), ('state', '=', 'approved')]).filtered(
                        lambda h: h.date.month == rec.permission_from.month and h.date.year == rec.permission_from.year
                    ).mapped('hours'))                    # get previous requested hours in same month and year
                    rec.used_hours = sum(self.env['permission.request'].sudo().search([
                        ('employee_id', '=', rec.employee_id.id)
                    ]).filtered(
                        lambda r: r.state == 'approved' and r.permission_from.month == rec.permission_from.month and r.permission_from.year == rec.permission_from.year
                    ).mapped('permission_hours'))
                    rec.remaining_hours = rec.total_hours + rec.total_extra_hours - rec.used_hours

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

    @api.depends('department_id')
    def compute_approver_ids(self):
        for rec in self:
            rec.approver_ids = False
            if rec.department_id and rec.department_id.manager_id.user_id:
                approvers = [rec.department_id.manager_id.user_id.id]
                hr_user = self.env['ir.config_parameter'].sudo().get_param('permission_request.permission_request_user_id') or False
                if hr_user:
                    hr_user_id = self.env['res.users'].browse(int(hr_user))
                    if hr_user_id:
                        approvers.append(hr_user_id.id)
                rec.approver_ids = [(6, 0, approvers)]

    def button_submit(self):
        if self.remaining_hours < self.permission_hours:
            raise ValidationError("You can't exceed your remaining hours!\nCreate request for more Hours")
        self.state = 'submitted'
        for approver in self.approver_ids:
            self.sudo().activity_schedule(
                'permission_request.mail_act_permission_request_submit',
                summary='Permission Request',
                note='Ask To Confirm Permission Request',
                user_id=approver.id)

    def button_approve(self):
        self.state = 'approved'

    def button_reject(self):
        self.state = 'rejected'

    @api.depends('remaining_hours', 'permission_hours')
    def compute_need_more_hours(self):
        for rec in self:
            rec.need_more_hours = bool(rec.remaining_hours < rec.permission_hours)

    def request_more_hours(self):
        return {
            'name': 'Request for more hours',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'permission.request.extra.hour',
            'context': {
                'default_permission_request_id': self.id,
                'default_employee_id': self.employee_id.id,
                'default_approver_ids': [(6, 0, self.approver_ids.ids)],
                'default_date': self.permission_from.date(),
            },
            'target': 'new',
        }

    @api.depends('extra_hour_ids')
    def compute_extra_hour_count(self):
        for rec in self:
            rec.extra_hour_count = len(rec.extra_hour_ids or [])
