from odoo import _, api, fields, models


class BidType(models.Model):
    _name = 'bid.type'
    _description = 'Bid Type'
    _order = 'id desc'

    name = fields.Char()
    company_id = fields.Many2one(
        'res.company',
        'Company',
        default=lambda self: self.env.company,
        required=True,
    )
