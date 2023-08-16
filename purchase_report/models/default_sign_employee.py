from odoo import fields, models, api


class DefaultSignEmployee(models.Model):
    _name = 'default.sign.employee'
    _description = 'Default Sign Employee'

    employee_id = fields.Many2one('hr.employee', required=True)
