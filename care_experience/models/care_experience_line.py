from odoo import _, api, fields, models


class ExperienceLine(models.Model):
    _name = 'care.experience.line'
    _description = 'Experience Line'

    experience_id = fields.Many2one('care.experience')
    name = fields.Char(required=True)
    start_date = fields.Date()
    expire_date = fields.Date()
    period = fields.Integer(string='Period in Months')
    state = fields.Selection(selection=[
        ('valid', 'Valid'),
        ('expired', 'Expired'),
    ])
