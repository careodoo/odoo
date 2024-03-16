# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class EmployeeShiftRequest(models.Model):
    _name = 'employee.shift.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Employee Request for Shifting'
    _order = 'id desc'

    def _default_approver_1(self):
        IPC = self.env['ir.config_parameter'].sudo()
        approver_1 = False
        approver_1_str = IPC.get_param('hr_employee_shift.employee_shift_approval_1')
        if approver_1_str:
            approver_1 = self.env['res.users'].browse(int(approver_1_str))
        return approver_1.id if approver_1 else False

    def _default_approver_2(self):
        IPC = self.env['ir.config_parameter'].sudo()
        approver_2 = False
        approver_2_str = IPC.get_param('hr_employee_shift.employee_shift_approval_2')
        if approver_2_str:
            approver_2 = self.env['res.users'].browse(int(approver_2_str))
        return approver_2.id if approver_2 else False

    def _default_approver_3(self):
        IPC = self.env['ir.config_parameter'].sudo()
        approver_3 = False
        approver_3_str = IPC.get_param('hr_employee_shift.employee_shift_approval_3')
        if approver_3_str:
            approver_3 = self.env['res.users'].browse(int(approver_3_str))
        return approver_3.id if approver_3 else False

    employee_id = fields.Many2one('hr.employee', required=True)
    image_128 = fields.Image("Image 128", related='employee_id.image_128', compute_sudo=True)
    avatar_128 = fields.Image("Avatar 128", related='employee_id.avatar_128', compute_sudo=True)
    current_department = fields.Many2one('hr.department', string='Old Department')
    new_department = fields.Many2one('hr.department', domain="[('id', '!=', current_department)]", required=True)
    date = fields.Date(string="Request Date")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent to Manager'),
        ('confirm', 'Submitted'),
        ('approval_1', 'First Approved'), ('refuse_1', 'First Refused'),
        ('approval_2', 'Second Approved'), ('refuse_2', 'Second Refused'),
        ('approval_3', 'Third Approved'), ('refuse_3', 'Third Refused'),
        ('done', 'Shifted'),
        ], string='State',default='draft', required=True, tracking=True)

    approver_1 = fields.Many2one('res.users', default=_default_approver_1)
    approver_2 = fields.Many2one('res.users', default=_default_approver_2)
    approver_3 = fields.Many2one('res.users', default=_default_approver_3)
    old_department_manager = fields.Many2one('res.users')
    new_department_manager = fields.Many2one('res.users')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)
    refuse_reason = fields.Char()
    working_hours_modifier = fields.Many2one('res.users', related='current_department.working_hours_modifier', store=True)
    working_hours = fields.Many2one('resource.calendar', related='employee_id.resource_calendar_id',
                                    store=True, readonly=False)
    active = fields.Boolean(default=True)
    show_shift_department = fields.Boolean()

    @api.model
    def create(self, vals):
        if vals.get('employee_id') and vals.get('current_department') and vals.get('new_department'):
            open_requests = self.env['employee.shift.request'].search([
                ('employee_id', '=', vals.get('employee_id')),
                ('current_department', '=', vals.get('current_department')),
                ('new_department', '=', vals.get('new_department')),
                ('state', 'not in', ['refuse_1', 'refuse_2', 'refuse_3', 'done'])  # closed states
            ])
            if open_requests:
                raise ValidationError("There is an open shift request (id={}) with the same inputs".format(open_requests[0].id))
        res = super(EmployeeShiftRequest, self).create(vals)
        return res

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            dept = self.employee_id.department_id
            self.current_department = dept.id
            if not dept.manager_id:
                raise ValidationError("{} is not linked to manager".format(dept.name))
            if not dept.manager_id.user_id:
                raise ValidationError("{} manager is not linked to user".format(dept.name))
            self.old_department_manager = dept.manager_id.user_id.id
            # in case department has approver users replace global approvers
            if dept.employee_shift_approval_1:
                self.approver_1 = dept.employee_shift_approval_1.id
                self.approver_2 = dept.employee_shift_approval_2.id if dept.employee_shift_approval_2 else False
                self.approver_3 = dept.employee_shift_approval_3.id if dept.employee_shift_approval_3 else False
            else:
                self.approver_1 = self._default_approver_1()
                self.approver_2 = self._default_approver_2()
                self.approver_3 = self._default_approver_3()

    @api.onchange('new_department')
    def onchange_new_department(self):
        if self.new_department:
            dept = self.new_department
            if not dept.manager_id:
                raise ValidationError("{} is not linked to manager".format(dept.name))
            if not dept.manager_id.user_id:
                raise ValidationError("{} manager is not linked to user".format(dept.name))
            self.new_department_manager = dept.manager_id.user_id.id

    def _prepare_request_record(self, approver):
        return {
            'employee_id': self.employee_id.id,
            'old_department': self.current_department.id,
            'new_department': self.new_department.id,
            'state': self.state,
            'approver': approver.id
        }

    # department manager must have access to his department request
    def send_to_manager(self):
        if not self.current_department.old_manager_approval:
            self.shift_confirm()
        else:
            self.write({'state': 'sent'})
            template = self.env.ref('hr_employee_shift.dept_shift_send_to_manager_template')
            self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)
            self.sudo().activity_schedule(
                'hr_employee_shift.mail_act_shift_create',
                summary='Department Shift Request',
                note='Ask To Submit Department Shift Request',
                user_id=self.old_department_manager.id)

    def shift_confirm(self):
        self.write({'state': 'confirm'})
        record = self._prepare_request_record(self.old_department_manager)
        self.env['employee.shift.request.record'].create(record)
        template = self.env.ref('hr_employee_shift.dept_shift_send_to_1_approve_template')
        self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)
        self.sudo().activity_schedule(
            'hr_employee_shift.mail_act_shift_create',
            summary='Department Shift Request',
            note='Ask To First Approve Department Shift Request',
            user_id=self.approver_1.id)

    def get_request_followers(self):
        followers = [self.new_department_manager.id]
        if self.approver_2:
            followers.append(self.approver_2.id)
        if self.approver_3:
            followers.append(self.approver_3.id)
        return followers

    def first_approve(self):
        if self.approver_2:
            self.write({'state': 'approval_1'})
            record = self._prepare_request_record(self.approver_1)
            self.env['employee.shift.request.record'].create(record)
            template = self.env.ref('hr_employee_shift.dept_shift_send_to_2_approve_template')
            self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)
            self.sudo().activity_schedule(
                'hr_employee_shift.mail_act_shift_create',
                summary='Department Shift Request',
                note='Ask To Second Approve Department Shift Request',
                user_id=self.approver_2.id)
        elif self.current_department.new_manager_approval:
            self.write({
                'state': 'approval_1',
                'show_shift_department': True,
            })
            record = self._prepare_request_record(self.approver_1)
            self.env['employee.shift.request.record'].create(record)
            template = self.env.ref('hr_employee_shift.dept_shift_send_to_new_dept_approve_template')
            self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)
            self.sudo().activity_schedule(
                'hr_employee_shift.mail_act_shift_create',
                summary='Department Shift Request',
                note='Ask To New Manager Approve Department Shift Request',
                user_id=self.new_department_manager.id)
        else:
            self.shift_department()

    def first_refuse(self):
        return {
            'name': 'Refuse Reason',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'request.refuse.reason',
            'target': 'new',
        }

    def second_approve(self):
        if self.approver_3:
            self.write({'state': 'approval_2'})
            record = self._prepare_request_record(self.approver_2)
            self.env['employee.shift.request.record'].create(record)
            template = self.env.ref('hr_employee_shift.dept_shift_send_to_3_approve_template')
            self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)
            self.sudo().activity_schedule(
                'hr_employee_shift.mail_act_shift_create',
                summary='Department Shift Request',
                note='Ask To Third Approve Department Shift Request',
                user_id=self.approver_3.id)
        elif self.current_department.new_manager_approval:
            self.write({
                'state': 'approval_2',
                'show_shift_department': True,
            })
            record = self._prepare_request_record(self.approver_2)
            self.env['employee.shift.request.record'].create(record)
            template = self.env.ref('hr_employee_shift.dept_shift_send_to_new_dept_approve_template')
            self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)
            self.sudo().activity_schedule(
                'hr_employee_shift.mail_act_shift_create',
                summary='Department Shift Request',
                note='Ask To New Manager Approve Department Shift Request',
                user_id=self.new_department_manager.id)
        else:
            self.shift_department()

    def third_approve(self):
        if self.current_department.new_manager_approval:
            self.write({
                'state': 'approval_3',
                'show_shift_department': True,
            })
            record = self._prepare_request_record(self.approver_3)
            self.env['employee.shift.request.record'].create(record)
            template = self.env.ref('hr_employee_shift.dept_shift_send_to_new_dept_approve_template')
            self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)
            self.sudo().activity_schedule(
                'hr_employee_shift.mail_act_shift_create',
                summary='Department Shift Request',
                note='Ask To New Manager Approve Department Shift Request',
                user_id=self.new_department_manager.id)
        else:
            self.shift_department()

    def shift_department(self):
        self.employee_id.with_context(shift_request=True).write({'department_id': self.new_department.id})
        self.write({
            'state': 'done',
            'show_shift_department': False
        })
        record = self._prepare_request_record(self.env.user)
        self.env['employee.shift.request.record'].create(record)
        followers = self.get_request_followers()
        for follower in followers:
            self.sudo().activity_schedule(
                'hr_employee_shift.mail_act_shift_create',
                summary='Department Shift Completed',
                note='Employee {} shifted from {} to {}'.format(
                    self.employee_id.name, self.current_department.name, self.new_department.name
                ),
                user_id=follower
            )
