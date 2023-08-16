# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    services_next_service_date_notify_reminder = fields.Integer(string='Next Service Date Reminder Days', config_parameter="care.services_next_service_date_notify_reminder")