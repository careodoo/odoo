from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def write(self, vals):
        if vals.get('standard_price', False) and not self.env.user.has_group('care_stock.group_product_update_request_approver'):
            raise ValidationError("Please create Product Update Request!")
        res = super(ProductTemplate, self).write(vals)
        return res
