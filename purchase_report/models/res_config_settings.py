# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sign_employee_1 = fields.Many2one('hr.employee', config_parameter='purchase_report.sign_employee_1')
    sign_employee_2 = fields.Many2one('hr.employee', config_parameter='purchase_report.sign_employee_2')
    sign_employee_3 = fields.Many2one('hr.employee', config_parameter='purchase_report.sign_employee_3')
