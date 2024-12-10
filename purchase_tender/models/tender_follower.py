from odoo import _, api, fields, models


class TenderFollower(models.Model):
    _name = 'purchase.tender.follower'
    _description = 'Tender Follower'
    _order = 'id desc'

    followers = fields.Many2many('res.users')
    company_id = fields.Many2one(
        'res.company',
        'Company',
        default=lambda self: self.env.company,
        required=True,
    )
