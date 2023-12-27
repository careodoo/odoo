from odoo import fields, models, api


class Attendance(models.Model):
    _inherit = 'hr.attendance'

    department_id = fields.Many2one('hr.department', related="employee_id.department_id", store=True)
    care_timesheet_id = fields.Many2one('care.timesheet')
