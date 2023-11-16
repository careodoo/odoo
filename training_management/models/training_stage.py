from odoo import fields, models, api


class TrainingStage(models.Model):
    _name = 'training.stage'
    _description = 'Training Stage'

    name = fields.Char(required=True)
    is_default = fields.Boolean(string='Default Stage')
