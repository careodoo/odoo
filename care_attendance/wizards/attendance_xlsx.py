from odoo import fields, models, api


class AttendanceXlsx(models.TransientModel):
    _name = 'hr.attendance.xlsx'
    _description = 'print attendance xlsx'

    date_from = fields.Date()
    date_to = fields.Date()
    department_ids = fields.Many2many('hr.department')

    def print_report(self):
        return self.env.ref("care_attendance.action_approval_print_xlsx_report").report_action(self)
