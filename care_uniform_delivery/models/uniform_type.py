from odoo import fields, models, api


class UniformType(models.Model):
    _name = 'uniform.type'
    _description = 'Uniform Type'
    _order = 'sequence'

    name = fields.Char()
    sequence = fields.Integer(default=10)
