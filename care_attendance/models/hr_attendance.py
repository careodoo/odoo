from odoo import fields, models, api


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    bulk_id = fields.Many2one('bulk.attendance')
    extra_department_id = fields.Many2one('hr.employee.extra.department')