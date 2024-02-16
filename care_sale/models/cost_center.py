from odoo import fields, models, api


class MonthlyCostCenter(models.Model):
    _inherit = 'cost.center.month'

    sale_order_ids = fields.Many2many('sale.order', string='Sale Orders')
