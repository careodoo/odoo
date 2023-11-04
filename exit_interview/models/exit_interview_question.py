from odoo import fields, models, api


class InterviewQuestion(models.Model):
    _name = 'interview.question'
    _description = 'Exit Interview Question'

    name = fields.Text(required=True)
    sequence = fields.Integer(default=10)
    yes_no = fields.Boolean('Yes/No Question')


class ExitInterviewQuestion(models.Model):
    _name = 'exit.interview.question'
    _description = 'Exit Interview Question'

    interview_id = fields.Many2one('exit.interview')
    name = fields.Text(required=True)
    sequence = fields.Integer(default=10)
    yes_no = fields.Boolean('Yes/No Question')
    answer = fields.Text()
