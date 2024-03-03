from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    validate_attendance_days = fields.Integer(config_parameter='to_attendance_device.validate_attendance_days', default=5)
