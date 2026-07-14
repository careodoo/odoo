# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CareIntegration(models.Model):
    _name = 'care.integration'
    _description = 'HR Integration'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    name = fields.Char(string='التكامل', required=True, translate=True)
    icon = fields.Char(string='أيقونة', default='🔌')
    status = fields.Selection([
        ('connected', 'متصل'),
        ('linked', 'مربوط'),
        ('pending', 'قيد الإعداد'),
        ('off', 'غير مفعّل'),
    ], string='الحالة', default='pending', required=True)
    description = fields.Char(string='الوظيفة', translate=True)
    note = fields.Text(string='تفاصيل')
