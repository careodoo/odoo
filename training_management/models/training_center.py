from odoo import fields, models, api


class TrainingCenter(models.Model):
    _name = 'training.center'
    _description = 'Training Center'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    location_id = fields.Many2one('hr.work.location', string='Training Center Location')
