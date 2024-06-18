from odoo import fields, models, api
from .qr_generator import generateQrCode
from odoo.http import request
from datetime import datetime


class ManpowerRequisition(models.Model):
    _name = 'manpower.requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Manpower Requisition'

    def generate_barcode(self):
        return str(int(datetime.now().timestamp()))

    def _get_hr_users(self):
        return self.env.ref("manpower_requisition.group_hr_manpower_hr").users.ids

    name = fields.Char(compute='compute_name', store=True)
    request_date = fields.Date(string='Date of Request')
    manager_id = fields.Many2one('hr.employee', string='Requesting Manager')
    location = fields.Char()
    required_title = fields.Many2many('hr.job', string='Title of position required')
    requirement_number = fields.Integer(string='No of Requirements')
    type = fields.Selection(selection=[
        ('overseas', 'Overseas'), ('local', 'Local')
    ], required=True, string='Overseas / Local')
    # reasons
    leaving_employee_id = fields.Many2many('hr.employee', 'manpower_employee_leaving_rel', 'manpower_id', 'emp_id', string='Employee Leaving')
    resignation_date = fields.Date(string='Resignation submitted on')
    transferred_employee_id = fields.Many2one('hr.employee', string='Employee being transferred')
    transfer_from = fields.Many2one('hr.department')
    transfer_to = fields.Many2one('hr.department')
    transfer_reason = fields.Char()
    project_id = fields.Many2one('project.project', string='Project Name')
    actual_headcount = fields.Integer()
    requirement_reason = fields.Text()
    specific_requirements = fields.Text()
    salary = fields.Float(string='Assigned salary for this requirements')
    working_hours = fields.Float()
    barcode = fields.Char(default=generate_barcode)
    qr_image = fields.Binary("QR Code", compute='_generate_qr_code')
    qr_url = fields.Char("QR Code", compute='_generate_qr_code')
    active = fields.Boolean(default=True)
    department_id = fields.Many2one('hr.department')
    department_manager_id = fields.Many2one('res.users', related='department_id.manager_id.user_id', store=True)
    parent_department_id = fields.Many2one('hr.department', related='department_id.parent_id', store=True)
    parent_manager_id = fields.Many2one('res.users', related='parent_department_id.manager_id.user_id', store=True)
    employee_ids = fields.Many2many('hr.employee', string='Requested Employees', domain="[('department_id', '=', department_id)]")
    need_hr_approve = fields.Boolean(string='Need HR Approve', default=True)
    hr_approve = fields.Boolean(string='HR Approve')
    hr_user_ids = fields.Many2many('res.users', default=_get_hr_users)
    need_manager_approve = fields.Boolean(default=True)
    manager_approve = fields.Boolean()
    need_parent_approve = fields.Boolean()
    state = fields.Selection(selection=[
        ('draft', 'Draft'), ('submit', 'Submitted'),
        ('approve', 'Approved'), ('reject', 'Reject')
    ], default='draft', tracking=True)

    @api.depends('requirement_number', 'required_title', 'location')
    def compute_name(self):
        for rec in self:
            rec.name = 'Request Manpower '
            if rec.requirement_number:
                rec.name += str(rec.requirement_number)
                rec.name += ' '
            if rec.required_title:
                rec.name += ','.join(rec.required_title.mapped('name'))
                rec.name += ' '
            if rec.location:
                rec.name += 'for '
                rec.name += rec.location

    def _generate_qr_code(self):
        for rec in self:
            qr_info = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            action_id = self.env.ref('manpower_requisition.manpower_requisition_action').id
            menu_id = self.env.ref('manpower_requisition.manpower_requisition_menu').id
            qr_info += '/web#id=%s&action=%s&model=%s&view_type=form&cids=&menu_id=%s' % (rec.id, action_id, 'manpower.requisition', menu_id)
            rec.qr_url = qr_info
            rec.qr_image = generateQrCode.generate_qr_code(qr_info)

    def button_submit(self):
        self.state = 'submit'
        if self.need_hr_approve and self.hr_user_ids:
            for user in self.hr_user_ids:
                self.sudo().activity_schedule(
                    'manpower_requisition.mail_act_manpower_submit',
                    summary='Manpower Requisition',
                    note='Ask To Approve Manpower Requisition',
                    user_id=user.id)

    def button_hr_approve(self):
        self.hr_approve = True
        if self.need_manager_approve and self.department_manager_id:
            self.sudo().activity_schedule(
                'manpower_requisition.mail_act_manpower_submit',
                summary='Manpower Requisition',
                note='Ask To Approve Manpower Requisition',
                user_id=self.department_manager_id.id)
        elif self.need_parent_approve and self.parent_manager_id:
            self.sudo().activity_schedule(
                'manpower_requisition.mail_act_manpower_submit',
                summary='Manpower Requisition',
                note='Ask To Approve Manpower Requisition',
                user_id=self.parent_manager_id.id)
        else:
            self.state = 'approve'

    def button_manager_approve(self):
        self.manager_approve = True
        if self.need_parent_approve and self.parent_manager_id:
            self.sudo().activity_schedule(
                'manpower_requisition.mail_act_manpower_submit',
                summary='Manpower Requisition',
                note='Ask To Approve Manpower Requisition',
                user_id=self.parent_manager_id.id)
        else:
            self.state = 'approve'

    def button_parent_approve(self):
        self.state = 'approve'

    def button_reject(self):
        self.state = 'reject'
