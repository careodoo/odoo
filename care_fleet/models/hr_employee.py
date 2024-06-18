from odoo import fields, models, api


class Employee(models.Model):
    _inherit = 'hr.employee'

    employee_cars_count = fields.Integer(groups=False)
