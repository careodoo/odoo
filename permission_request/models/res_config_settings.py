from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    permission_request_hours = fields.Integer(config_parameter='permission_request.permission_request_hours', default=4)
    permission_request_user_id = fields.Many2one('res.users', config_parameter='permission_request.permission_request_user_id')
