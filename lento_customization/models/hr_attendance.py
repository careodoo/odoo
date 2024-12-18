# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    personal_id = fields.Integer(string="Personal ID", required=False, related="employee_id.personal_id")
