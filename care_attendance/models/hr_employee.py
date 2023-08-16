from odoo import fields, models, api
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    extra_department_ids = fields.One2many('hr.employee.extra.department', 'employee_id')

    def unlink(self):
        if not self.env.user.has_group('care_attendance.group_delete_employee_user'):
            raise UserError("You are not allowed to delete an employee!")
        return super(HrEmployee, self).unlink()

class HrEmployeeExtraDepartment(models.Model):
    _name = 'hr.employee.extra.department'
    _description = 'Extra Department'

    employee_id = fields.Many2one('hr.employee')
    employee_department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    employee_calendar_id = fields.Many2one('resource.calendar', related='employee_id.resource_calendar_id', store=True)
    department_id = fields.Many2one('hr.department', domain="[('id', '!=', employee_department_id)]", required=True)
    calendar_id = fields.Many2one('resource.calendar', required=True)


