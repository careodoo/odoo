from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    employee_shift_approval_1 = fields.Many2one('res.users', string='First Approval of Employee Shift Request',
                                                config_parameter='hr_employee_shift.employee_shift_approval_1',
                                                help='First Approval of Employee Shift Request')
    employee_shift_approval_2 = fields.Many2one('res.users', string='Second Approval of Employee Shift Request',
                                                config_parameter='hr_employee_shift.employee_shift_approval_2',
                                                help='Second Approval of Employee Shift Request')
    employee_shift_approval_3 = fields.Many2one('res.users', string='Third Approval of Employee Shift Request',
                                                config_parameter='hr_employee_shift.employee_shift_approval_3',
                                                help='Third Approval of Employee Shift Request')

