from odoo import fields, models, api


class TrainingRoom(models.Model):
    _name = 'training.room'
    _description = 'Training Class Room'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    center_id = fields.Many2one('training.center', string='Training Center', required=True)
