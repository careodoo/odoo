from odoo import fields, models, api


class DefaultSignEmployee(models.Model):
    _name = 'default.sign.employee'
    _order = 'sequence'
    _description = 'Default Sign Employee'

    sequence = fields.Integer(default=10)
    employee_id = fields.Many2one('hr.employee', required=True)
    option_online = fields.Boolean(default=True, string='Online')
    option_print = fields.Boolean(default=True, string='Print')
