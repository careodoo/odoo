from odoo import fields, models, api


class DefaultSaleSignEmployee(models.Model):
    _name = 'default.sale.sign.employee'
    _description = 'Default Sale Sign Employee'

    employee_id = fields.Many2one('hr.employee', required=True)
