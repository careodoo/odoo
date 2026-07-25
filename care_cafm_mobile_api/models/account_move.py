# -*- coding: utf-8 -*-
"""Invoice ↔ UPayments bridge.

A single reference stamped on the invoice when the client starts an in-app
payment, so the gateway's webhook can find the exact invoice to settle.
"""
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    x_upay_ref = fields.Char(
        string='مرجع دفع UPayments', copy=False, index=True, tracking=True,
        help='المرجع الفريد لآخر محاولة دفع عبر البوابة داخل التطبيق.')
