from odoo import models, fields


class LastUpdate(models.Model):
    _name = "last.product.update"

    name = fields.Char(string="Field")
    before_value = fields.Char(string="Before Value")
    after_value = fields.Char(string="After Value")
    product_id = fields.Many2one(comodel_name="product.product", string="Product")