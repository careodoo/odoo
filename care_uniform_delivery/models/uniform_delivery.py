from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class UniformDelivery(models.Model):
    _name = 'uniform.delivery'
    _description = 'Uniform Delivery'
    _order = 'sequence'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    uniform_type_id = fields.Many2one('uniform.type')
    date = fields.Date()
    employee_id = fields.Many2one('hr.employee')
    employee_ids = fields.Many2many('hr.employee')
    signature = fields.Binary(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)

    @api.constrains('employee_id', 'employee_ids')
    def _check_recipient(self):
        for rec in self:
            if rec.employee_id and rec.employee_ids:
                raise ValidationError(_(
                    "A uniform delivery cannot have both an individual employee and bulk employees. "
                    "Use the individual employee for an individual delivery, or the bulk employees for a bulk delivery."
                ))
            if not rec.employee_id and not rec.employee_ids:
                raise ValidationError(_(
                    "A uniform delivery must have a recipient: set the individual employee "
                    "or the bulk employees."
                ))
