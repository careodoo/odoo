from odoo import fields, models, api


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
