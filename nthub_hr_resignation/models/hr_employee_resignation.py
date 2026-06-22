# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo import models, fields, api, _
from datetime import date
from odoo.exceptions import UserError
from dateutil import relativedelta
import time

resignation_states = [('draft', 'Draft'),
                      ('submit', 'Waiting HR Approval'),
                      ('hr_dept', 'Waiting Finance Approval'),
                      ('finance_dept', 'Waiting Done'),
                      ('done', 'Done'),
                      ('refuse', 'Refused')]


class HrEmployeeResignation(models.Model):
    _name = 'hr.employee.resignation'
    _inherit = 'mail.thread'
    _description = "Employee Resignation"
    _rec_name = 'employee_name'

    def unlink(self):
        """
            To remove the record, which is not in 'confirm','done' state
        """
        for objects in self:
            if objects.state in ['submit', 'done']:
                raise UserError(_('You cannot remove the record which is in %s state!') % objects.state)
        return super(HrEmployeeResignation, self).unlink()

    # Fields Hr Employee resignation
    name = fields.Char(default='New')
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True,
                                  default=lambda self: self.env['hr.employee'].get_employee())
    employee_name = fields.Char(string='Name', related='employee_id.name')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id',
                                    string='Department', store=True)
    # last_working_day = fields.Date('Last Day of Work', related='employee_id.date_of_leave', store=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.user.company_id)

    approved_date = fields.Datetime('Resignation Approve Date', readonly=True)
    leave_date = fields.Date('Leave Date')
    ticket_date = fields.Date('Ticket Date', default=fields.Date.today())
    approved_by = fields.Many2one('res.users', 'Approved by', readonly=True)
    state = fields.Selection(resignation_states, 'Status', default='draft')
    resignation_type = fields.Selection(
        [('resignation', 'Resignation'), ('termination', 'Termination'), ('death', 'Death')])
    reason = fields.Text()
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    # @api.model_create_multi
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('hr.employee.resignation') or 'New'
        record = super(HrEmployeeResignation, self).create(vals)
        return record

    def action_submit(self):
        self.ensure_one()
        self.state = 'submit'
        date_from = date(self.leave_date.year, self.leave_date.month, 1)
        date_to = date_from + relativedelta.relativedelta(day=self.leave_date.day)
        contract_ids = self.employee_id.get_active_contracts(date_to)
        if not contract_ids:
            raise UserError(_('Please define contract for selected Employee!'))
        self.employee_id.date_of_leave = self.leave_date

    def action_hr_approve(self):
        self.ensure_one()
        self.state = 'hr_dept'

    def action_finance_approve(self):
        self.ensure_one()
        self.state = 'finance_dept'

    def action_resignation_refuse(self):
        """
            sent the status of generating his/her resignation in Refuse state
        """
        self.ensure_one()
        self.state = 'refuse'

    def action_resignation_done(self):
        """
            sent the status of generating his/her resignation in Confirm state
            and convert employee active state to false fot archiving him
        """
        self.ensure_one()
        self.state = 'done'
        self.approved_date = fields.Datetime.now()
        self.approved_by = self.env.user
        self.employee_id.active = False
        self.employee_id.resigned = True
        self.employee_id.resignation_type = self.resignation_type

    def action_set_to_draft(self):
        """
            sent the status of generating his/her resignation in Set to Draft state
        """
        self.ensure_one()
        self.state = 'draft'
