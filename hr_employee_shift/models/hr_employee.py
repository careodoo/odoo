from odoo import fields, models, api
from odoo.exceptions import ValidationError


class Employee(models.Model):
    _inherit = 'hr.employee'

    shift_request_records = fields.One2many('employee.shift.request.record', 'employee_id')

    def write(self, vals):
        res = super(Employee, self).write(vals)
        shift_request = self.env.context.get('shift_request', False)
        if vals.get('department_id'):
            if not self.env.user.has_group('hr_employee_shift.group_direct_shift_user') and not shift_request:
                raise ValidationError('You are not allowed to modify department directly, you should create shift request')
        return res


class EmployeeShiftRequestRecord(models.Model):
    _name = 'employee.shift.request.record'
    _description = 'Employee Shift Request History'

    employee_id = fields.Many2one('hr.employee')
    old_department = fields.Many2one('hr.department')
    new_department = fields.Many2one('hr.department')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent to Manager'),
        ('confirm', 'Confirmed'),
        ('approval_1', 'First Approved'), ('refuse_1', 'First Refused'),
        ('approval_2', 'Second Approved'), ('refuse_2', 'Second Refused'),
        ('approval_3', 'Third Approved'), ('refuse_3', 'Third Refused'),
        ('done', 'Shifted')], string='State')
    approver = fields.Many2one('res.users')
