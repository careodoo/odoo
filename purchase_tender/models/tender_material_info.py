from odoo import _, api, fields, models


class TenderMaterialInfo(models.Model):
    _name = 'purchase.tender.material.info'
    _description = 'Purchase Tender Material Info'
    _order = 'id desc'

    name = fields.Char(required=True, string="Description")
    sequence = fields.Integer(default=10)
    action = fields.Char()
    tender_id = fields.Many2one('purchase.tender')
    company_id = fields.Many2one(
        'res.company',
        'Company',
        default=lambda self: self.env.company,
        required=True,
    )
