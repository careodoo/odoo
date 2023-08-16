# -*- coding: utf-8 -*-

from odoo import models, fields, api


class TenderRecord(models.Model):
    _name = 'purchase.tender.record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Purchase Tender Record'
    _order = 'id desc'

    name = fields.Char()
    source = fields.Many2one('res.partner')
    source_no = fields.Char()
    date = fields.Date()
    content = fields.Text()
    state = fields.Selection(selection=[
        ('care', 'Care'), ('tenders', 'Tenders'),
        ('related', 'Related'), ('upcoming', 'Upcoming'),
    ])
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)