from odoo import fields, models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    approval_request_id = fields.Many2one('approval.request')
