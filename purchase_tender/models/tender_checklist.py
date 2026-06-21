from odoo import fields, models


class TenderChecklist(models.Model):
    _name = 'purchase.tender.checklist'
    _description = 'Tender Pre-bid Checklist'
    _order = 'sequence, id'

    tender_id = fields.Many2one('purchase.tender', ondelete='cascade', required=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, string='المهمة')
    is_done = fields.Boolean(string='منجز')
    responsible_id = fields.Many2one('res.users', string='المسؤول')
    deadline = fields.Date(string='الموعد')
    note = fields.Char(string='ملاحظات')
    company_id = fields.Many2one(related='tender_id.company_id', store=True)
