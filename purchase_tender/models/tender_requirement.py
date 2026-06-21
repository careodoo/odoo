from odoo import fields, models


class TenderRequirement(models.Model):
    _name = 'purchase.tender.requirement'
    _description = 'Tender Requirement (extracted from the document)'
    _order = 'category, sequence, id'

    tender_id = fields.Many2one('purchase.tender', ondelete='cascade', required=True)
    sequence = fields.Integer(default=10)
    category = fields.Selection([
        ('document', 'مستند'),
        ('equipment', 'معدة'),
        ('tool', 'أداة'),
        ('condition', 'شرط'),
        ('info', 'معلومة'),
    ], string='النوع', required=True, default='document')
    name = fields.Char(string='البند', required=True)
    detail = fields.Char(string='التفاصيل')
    qty = fields.Integer(string='الكمية')
    is_ready = fields.Boolean(string='متوفّر / مُنجز')
    company_id = fields.Many2one(related='tender_id.company_id', store=True)
