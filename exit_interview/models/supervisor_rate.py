from odoo import fields, models, api


class SupervisorRate(models.Model):
    _name = 'supervisor.rate'
    _description = 'Supervisor Rate'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)


class ExitInterviewSupervisorRate(models.Model):
    _name = 'exit.interview.supervisor.rate'
    _description = 'Supervisor Rate'

    interview_id = fields.Many2one('exit.interview')
    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    rate = fields.Selection(selection=[
        ('0', 'Very Poor'), ('1', 'Poor'), ('2', 'Bad'),
        ('3', 'Average'), ('4', 'Good'), ('5', 'Excellent'),
    ])

