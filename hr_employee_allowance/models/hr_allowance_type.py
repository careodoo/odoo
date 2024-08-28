from odoo import models, fields


class HrAllowanceType(models.Model):
    _name = 'hr.allowance.type'
    _description = 'Hr Allowance Type'

    name = fields.Char(
        'Type',
        required=True,
    )

    package_ids = fields.One2many(
        'hr.allowance.package',
        'allowance_type_id',
        'Allowance Packages',
    )
