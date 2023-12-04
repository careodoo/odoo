from odoo import fields, models, api


class DefaultSignEmployee(models.Model):
    _name = 'default.sign.employee'
    _description = 'Default Sign Employee'

    employee_id = fields.Many2one('hr.employee', required=True)
    option_online = fields.Boolean(default=True, string='Online')
    option_print = fields.Boolean(default=True, string='Print')
