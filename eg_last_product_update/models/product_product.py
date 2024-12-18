from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = "product.product"

    last_product_update_ids = fields.One2many(comodel_name="last.product.update", inverse_name="product_id", string="Last Update")

    def write(self, vals):
        for product_id in self:
            last_product_update_obj = self.env['last.product.update']
            sale_ok = False
            purchase_ok = False
            lst_price = 0
            standard_price = 0
            if 'sale_ok' in vals:
                sale_ok = product_id.sale_ok
            if 'purchase_ok' in vals:
                purchase_ok = product_id.purchase_ok
            if 'list_price' in vals:
                lst_price = product_id.list_price
            if 'standard_price' in vals:
                standard_price = product_id.standard_price
            res = super(ProductProduct, self).write(vals)
            if len(self.last_product_update_ids) >= 10:
                self.last_product_update_ids[0].unlink()
            if 'sale_ok' in vals:
                last_product_update_obj.create({
                    'name': 'Can be Sold',
                    'product_id': product_id.id,
                    'before_value': 'True' if sale_ok else 'False',
                    'after_value': 'True' if product_id.sale_ok else 'False',
                })
            if 'purchase_ok' in vals:
                last_product_update_obj.create({
                    'name': 'Can be Purchased',
                    'product_id': product_id.id,
                    'before_value': 'True' if purchase_ok else 'False',
                    'after_value': 'True' if product_id.purchase_ok else 'False',
                })
            if 'lst_price' in vals:
                last_product_update_obj.create({
                    'name': 'Sale Price',
                    'product_id': product_id.id,
                    'before_value': lst_price,
                    'after_value': product_id.lst_price
                })
            if 'standard_price' in vals:
                last_product_update_obj.create({
                    'name': 'Cost',
                    'product_id': product_id.id,
                    'before_value': standard_price,
                    'after_value': product_id.standard_price
                })
            return res