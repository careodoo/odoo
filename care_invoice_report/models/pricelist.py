from odoo import fields, models, api


class PricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    price_per_day = fields.Float(compute='compute_price_per_day_hour', store=True, digits='Product Price')
    price_per_hour = fields.Float(compute='compute_price_per_day_hour', store=True, digits='Product Price')

    @api.depends('product_tmpl_id', 'fixed_price', 'product_tmpl_id.labor_service', 'product_tmpl_id.days_per_month', 'product_tmpl_id.hours_per_day')
    def compute_price_per_day_hour(self):
        for rec in self:
            rec.price_per_day = 0
            rec.price_per_hour = 0
            if rec.product_tmpl_id and rec.product_tmpl_id.labor_service and rec.product_tmpl_id.days_per_month and rec.product_tmpl_id.hours_per_day:
                rec.price_per_day = rec.fixed_price / rec.product_tmpl_id.days_per_month
                rec.price_per_hour = rec.price_per_day / rec.product_tmpl_id.hours_per_day
