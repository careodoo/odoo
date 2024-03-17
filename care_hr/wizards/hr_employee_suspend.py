from odoo import fields, models, api


class EmployeeSuspend(models.TransientModel):
    _name = 'hr.employee.suspend'
    _description = 'Employee Suspend'

    employee_id = fields.Many2one('hr.employee')
    reason = fields.Text()
    date = fields.Date()
    unsuspend = fields.Boolean()
    can_print_reports = fields.Boolean()
    can_edit = fields.Boolean()

    def button_suspend(self):
        if self.unsuspend:
            self.employee_id.with_context(ignore_suspend=True).write({
                'suspend_date': False,
                'suspend_reason': False,
                'suspend_by': False,
                'can_print_reports': False,
                'can_edit': False,
            })
        else:
            self.employee_id.with_context(ignore_suspend=True).write({
                'suspend_date': self.date,
                'suspend_reason': self.reason,
                'suspend_by': self.create_uid.id,
                'can_print_reports': self.can_print_reports,
                'can_edit': self.can_edit,
            })
