from odoo import fields, models, api


class Partner(models.Model):
    _inherit = 'res.partner'

    disable_notification = fields.Boolean()