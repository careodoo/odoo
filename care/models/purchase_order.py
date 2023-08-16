from odoo import fields, models, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    from_custody = fields.Boolean()
    custody = fields.Many2one('custody', domain=[('is_active', '=', True)])
