from odoo import models, fields, api


class HrAllowanceRequest(models.Model):
    _name = 'hr.allowance.request'
    _description = 'Hr Allowance Request'

    allowance_type_id = fields.Many2one(
        'hr.allowance.type',
        'Allowance Type',
        required=True,
    )

    allowance_package_id = fields.Many2one(
        comodel_name='hr.allowance.package',
        string='Allowance Package',
        domain="[('allowance_type_id','=',allowance_type_id)]",
        required=True,
    )

    employee_id = fields.Many2one(
        'hr.employee',
        'Employee',
        required=True,
    )
    start_date = fields.Date(
        string='From',
        required=True,
    )
    end_date = fields.Date(
        string='To',
        required=True,
    )

    @api.depends('employee_id', 'allowance_type_id', 'allowance_package_id')
    def _compute_display_name(self):
        for request in self:
            request.display_name = f'{request.employee_id.name}-{request.allowance_type_id.name}-{request.allowance_package_id.name}'
