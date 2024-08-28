from odoo import models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def action_allowance_request(self):
        return {
            'name': 'Request Allowance',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.allowance.request',
            'view_id': self.env.ref('hr_employee_allowance.hr_allowance_request_form_view').id,
            'context': {
                'default_employee_id': self.id
            },
        }
