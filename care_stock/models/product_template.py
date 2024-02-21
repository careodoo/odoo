from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    @api.model
    def create(self, vals):
        res = super(ProductTemplate, self).create(vals)
        if not res.default_code:
            res.default_code = self.env['ir.sequence'].next_by_code('product.internal.reference')
        return res

    def write(self, vals):
        if vals.get('standard_price', False) and not self.env.user.has_group('care_stock.group_product_update_request_approver'):
            raise ValidationError("Please create Product Update Request!")
        res = super(ProductTemplate, self).write(vals)
        return res

    def generate_internal_reference(self):
        products = self.env['product.template'].browse(self.env.context.get('active_ids')) or self
        for product in products:
            product.default_code = self.env['ir.sequence'].next_by_code('product.internal.reference')
