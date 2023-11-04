from odoo import fields, models, api


class OrganizationRate(models.Model):
    _name = 'organization.rate'
    _description = 'Organization Rate'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)


class ExitInterviewOrganizationRate(models.Model):
    _name = 'exit.interview.organization.rate'
    _description = 'Exit InterviewOrganization Rate'

    interview_id = fields.Many2one('exit.interview')
    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    rate = fields.Selection(selection=[
        ('0', 'Very Poor'), ('1', 'Poor'), ('2', 'Bad'),
        ('3', 'Average'), ('4', 'Good'), ('5', 'Excellent'),
    ])
