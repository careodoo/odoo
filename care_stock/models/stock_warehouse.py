from odoo import fields, models, api


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    warehouse_address = fields.Html()
