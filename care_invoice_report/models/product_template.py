from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    labor_service = fields.Boolean()
    days_per_month = fields.Integer()
    hours_per_day = fields.Integer()
