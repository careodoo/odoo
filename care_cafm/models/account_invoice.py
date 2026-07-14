# -*- coding: utf-8 -*-
"""Client-side invoice approval: the client accepts or rejects each invoice from
the portal (with comments). A rejection flags the invoice for us to revise and
re-send, and the state is recorded on the invoice itself."""
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    cafm_client_approval = fields.Selection([
        ('pending', 'بانتظار رد العميل'),
        ('accepted', 'مقبولة من العميل'),
        ('rejected', 'مرفوضة من العميل'),
    ], string='موافقة العميل', default='pending', copy=False, tracking=True, index=True)
    cafm_client_comment = fields.Text(string='تعليق العميل', copy=False)
    cafm_client_approval_date = fields.Datetime(string='تاريخ رد العميل', copy=False)
    cafm_needs_resend = fields.Boolean(
        string='بحاجة لإعادة الإرسال', copy=False,
        help='يُرفع تلقائياً عند رفض العميل للفاتورة — تُراجَع وتُعاد.')
