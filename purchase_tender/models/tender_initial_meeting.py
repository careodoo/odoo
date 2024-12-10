from odoo import _, api, fields, models


class TenderInitialMeeting(models.Model):
    _name = 'purchase.tender.initial.meeting'
    _description = 'Purchase Tender Initial Meeting'
    _order = 'id desc'

    name = fields.Char(required=True, string="Description")
    sequence = fields.Integer(default=10)
    date = fields.Date()
    file = fields.Binary()
    tender_id = fields.Many2one('purchase.tender')
    company_id = fields.Many2one(
        'res.company',
        'Company',
        default=lambda self: self.env.company,
        required=True,
    )
