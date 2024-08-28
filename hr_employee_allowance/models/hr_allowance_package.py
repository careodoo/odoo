from odoo import models, fields


class HrAllowancePackage(models.Model):
    _name = 'hr.allowance.package'
    _description = 'Hr Allowance Package'

    name = fields.Char(
        'Package',
        required=True,
    )

    allowance_type_id = fields.Many2one(
        'hr.allowance.type',
        'Type',
    )
