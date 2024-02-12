from odoo import fields, models, api


class Product(models.Model):
    _inherit = 'product.product'

    opening_balance_date = fields.Date(compute='compute_opening_balance_date')

    def compute_opening_balance_date(self):
        for rec in self:
            rec.opening_balance_date = False
            inventory = self.env['stock.inventory'].search([('state', '=', 'done')]).filtered(
                lambda i: rec.id in i.product_ids.ids
            ).sorted(key='date', reverse=True)
            if inventory:
                rec.opening_balance_date = inventory[0].date
