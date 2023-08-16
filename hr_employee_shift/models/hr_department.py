from odoo import fields, models, api


class Department(models.Model):
    _inherit = 'hr.department'

    employee_shift_approval_1 = fields.Many2one('res.users', string='Approver#1')
    employee_shift_approval_2 = fields.Many2one('res.users', string='Approver#2')
    employee_shift_approval_3 = fields.Many2one('res.users', string='Approver#3')
    working_hours_modifier = fields.Many2one('res.users',
                                             domain="[('id', 'in', [employee_shift_approval_1, employee_shift_approval_2, employee_shift_approval_3])]")
