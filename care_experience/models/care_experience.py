from odoo import fields, models, api


class Experience(models.Model):
    _name = 'care.experience'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Experience'
    _order = 'id desc'

    name = fields.Char(required=True)
    line_ids = fields.One2many('care.experience.line', 'experience_id')
    partner_id = fields.Many2one('res.partner', string='Organization')
    contract_amount = fields.Float()
    period = fields.Integer(string='Period in Months')
    labor_quantity = fields.Integer()
    start_date = fields.Date()
    expire_date = fields.Date()
    contract_type = fields.Selection(selection=[
        ('government', 'Government'), ('commercials', 'Commercials')
    ])
    kanban_state = fields.Selection(selection=[
        ('normal', 'Normal'), ('done', 'Done'), ('blocked', 'Blocked')
    ])
    notes = fields.Text()
    active = fields.Boolean(default=True)
    state = fields.Selection(selection=[
        ('valid', 'Valid'), ('expired', 'Expired')
    ])


class ExperienceLine(models.Model):
    _name = 'care.experience.line'
    _description = 'Experience Line'

    experience_id = fields.Many2one('care.experience')
    name = fields.Char(required=True)
    start_date = fields.Date()
    expire_date = fields.Date()
    period = fields.Integer(string='Period in Months')
    state = fields.Selection(selection=[
        ('valid', 'Valid'), ('expired', 'Expired')
    ])
