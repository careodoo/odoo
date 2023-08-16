# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, date
import pytz
from dateutil import relativedelta


class BulkAttendance(models.Model):
    _name = 'bulk.attendance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'bulk attendance'
    _order = 'id desc'

    def get_original_department_ids(self):
        department_manager_emp = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)],
                                                                limit=1)
        department_ids = self.env['hr.department'].search([('manager_id', '=', department_manager_emp.id)])
        return department_ids.ids if department_ids else self.env['hr.department']

    def get_department_ids(self):
        department_manager_emp = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)],
                                                                limit=1)
        department_ids = self.env['hr.department'].search([('manager_id', '=', department_manager_emp.id)])
        return department_ids.ids if department_ids else self.env['hr.department']

    def _default_approver(self):
        IPC = self.env['ir.config_parameter'].sudo()
        approver = False
        approver_str = IPC.get_param('care_attendance.bulk_attendance_approval')
        if approver_str:
            approver = self.env['res.users'].browse(int(approver_str))
        return approver.id if approver else False

    name = fields.Char(required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    type = fields.Selection([
        ('attendance', 'Attendance'),
        ('absence', 'Absence'),
    ], default='attendance')
    department_manager = fields.Many2one('res.users', default=lambda self: self.env.user)
    approver = fields.Many2one('res.users', default=_default_approver)
    original_department_ids = fields.Many2many(
        'hr.department', 'original_attendance_department_rel',
        'attendance_id', 'department_id', default=get_original_department_ids)
    department_ids = fields.Many2many(
        'hr.department', 'attendance_department_rel',
        'attendance_id2', 'department_id2', default=get_department_ids, domain="[('id', 'in', original_department_ids)]")

    employee_ids = fields.Many2many(
        'hr.employee', 'attendance_employee_rel',
        'attendance_id', 'employee_id', domain="[('department_id', 'in', department_ids)]")
    absent_employee_ids = fields.Many2many(
        'hr.employee', 'absent_employee_rel',
        'attendance_id', 'employee_id', domain="[('department_id', 'in', department_ids)]")

    bulk_date = fields.Date(default=fields.Date.today, string='Date')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Submitted'),
        ('approved', 'Approved'), ('refuse', 'Refused'),
    ], string='State', default='draft', required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.company)
    refuse_reason = fields.Char()
    extra_department_ids = fields.Many2many('hr.employee.extra.department',
                                            domain="[('department_id', 'in', department_ids)]")

    def button_confirm(self):
        # if (not self.employee_ids and self.type == 'attendance') and (not self.absent_employee_ids and self.type == 'absence') and not self.extra_department_ids:
        #     raise ValidationError("Select employees first!")

        self.write({'state': 'confirm'})
        template = self.env.ref('care_attendance.bulk_attendance_send_to_approver_template')
        self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)
        self.sudo().activity_schedule(
            'care_attendance.mail_act_bulk_attendance_create',
            summary='Bulk Attendance',
            note='Ask To Approve Bulk Attendance',
            user_id=self.approver.id)

    def button_draft(self):
        self.state = 'draft'

    def button_approve(self):
        t = datetime.combine(self.bulk_date, datetime.min.time()) if self.bulk_date else datetime.today()
        if self.type == 'absence':
            all_dept_employees = self.env['hr.employee'].search([('department_id', 'in', self.department_ids.ids)])
            attend_employees = all_dept_employees.filtered(lambda emp: emp.id not in self.absent_employee_ids.ids)
        else:
            attend_employees = self.employee_ids
        for emp in attend_employees:
            today_calendar_lines = emp.resource_calendar_id.attendance_ids.filtered(
                lambda att: int(att.dayofweek) == t.isoweekday() - 1)
            if not today_calendar_lines:
                raise ValidationError("working hours for {} has no {} lines".format(emp.name, t.strftime("%A")))
            tz = pytz.timezone(emp.tz)
            offset = tz.utcoffset(t).seconds / 3600
            check_in = datetime(t.year, t.month, t.day, int(today_calendar_lines[0].hour_from)) - relativedelta.relativedelta(hours=offset)
            check_out = False
            if self.bulk_date < date.today():
                if len(today_calendar_lines) == 1:
                    check_out = datetime(t.year, t.month, t.day, int(today_calendar_lines[0].hour_to)) - relativedelta.relativedelta(hours=offset)
                elif len(today_calendar_lines) > 1:
                    check_out = datetime(t.year, t.month, t.day, int(today_calendar_lines[1].hour_to)) - relativedelta.relativedelta(hours=offset)

            self.env['hr.attendance'].create({
                'employee_id': emp.id,
                'check_in': check_in,
                'check_out': check_out,
                'bulk_id': self.id
            })
        # extra departments
        if self.extra_department_ids:
            for extra in self.extra_department_ids:
                today_calendar_lines = extra.calendar_id.attendance_ids.filtered(
                    lambda att: int(att.dayofweek) == t.isoweekday() - 1)
                if not today_calendar_lines:
                    raise ValidationError("extra working hours for {} has no {} lines".format(extra.employee_id.name, t.strftime("%A")))
                tz = pytz.timezone(extra.employee_id.tz)
                offset = tz.utcoffset(t).seconds / 3600
                check_in = datetime(t.year, t.month, t.day,
                                    int(today_calendar_lines[0].hour_from)) - relativedelta.relativedelta(hours=offset)
                check_out = False
                if self.bulk_date < date.today():
                    if len(today_calendar_lines) == 1:
                        check_out = datetime(t.year, t.month, t.day, int(today_calendar_lines[0].hour_to)) - relativedelta.relativedelta(hours=offset)
                    elif len(today_calendar_lines) > 1:
                        check_out = datetime(t.year, t.month, t.day, int(today_calendar_lines[1].hour_to)) - relativedelta.relativedelta(hours=offset)
                self.env['hr.attendance'].create({
                    'employee_id': extra.employee_id.id,
                    'check_in': check_in,
                    'check_out': check_out,
                    'bulk_id': self.id,
                    'extra_department_id': extra.id
                })
        template = self.env.ref('care_attendance.bulk_attendance_approved_template')
        self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)
        self.sudo().activity_schedule(
            'care_attendance.mail_act_bulk_attendance_create',
            summary='Bulk Attendance',
            note='Bulk Attendance Approved',
            user_id=self.department_manager.id)
        self.state = 'approved'

    def button_refuse(self):
        return {
            'name': 'Refuse Reason',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'attendance.refuse.reason',
            'target': 'new',
        }

    @api.model
    def cron_bulk_check_out(self):
        attendances = self.env['hr.attendance'].search([('bulk_id', '!=', False), ('check_out', '=', False)])
        for att in attendances:
            t = datetime.combine(att.bulk_id.bulk_date, datetime.min.time()) if att.bulk_id.bulk_date else datetime.today()
            if att.extra_department_id:
                today_calendar_lines = att.extra_department_id.calendar_id.attendance_ids.filtered(
                    lambda att: int(att.dayofweek) == t.isoweekday() - 1)
            else:
                today_calendar_lines = att.employee_id.resource_calendar_id.attendance_ids.filtered(
                    lambda att: int(att.dayofweek) == t.isoweekday() - 1)
            tz = pytz.timezone(att.employee_id.tz)
            offset = tz.utcoffset(t).seconds / 3600

            if len(today_calendar_lines) == 1:
                check_out = datetime(t.year, t.month, t.day,
                                    int(today_calendar_lines[0].hour_to)) - relativedelta.relativedelta(hours=offset)
                if datetime.now() >= check_out:
                    att.check_out = check_out
            elif len(today_calendar_lines) > 1:
                check_out = datetime(t.year, t.month, t.day,
                                    int(today_calendar_lines[1].hour_to)) - relativedelta.relativedelta(hours=offset)
                if datetime.now() >= check_out:
                    att.check_out = check_out

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('bulk.attendance') or _('New')

        result = super(BulkAttendance, self).create(vals)
        return result
