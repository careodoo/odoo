from odoo import _, api, fields, models


class TenderVehicleAnalysis(models.Model):
    _name = 'purchase.tender.vehicle.analysis'
    _description = 'Purchase Tender Vehicle Analysis'
    _order = 'id desc'

    name = fields.Char(required=True, string="Description")
    sequence = fields.Integer(default=10)
    qty = fields.Float()
    tender_id = fields.Many2one('purchase.tender')
    company_id = fields.Many2one(
        'res.company',
        'Company',
        default=lambda self: self.env.company,
        required=True,
    )
