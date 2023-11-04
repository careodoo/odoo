from odoo import fields, models, api


class ExitInterview(models.Model):
    _name = 'exit.interview'
    _description = 'Exit Interview'

    employee_id = fields.Many2one('hr.employee', required=True)
    employee_code = fields.Char()
    date = fields.Date()
    join_date = fields.Date(string='DOJ')
    current_designation = fields.Char()
    supervisor_id = fields.Many2one('hr.employee', string='Name of the Supervisor')
    resignation_date = fields.Date(string='Date of Resignation')
    last_working_day = fields.Date()
    contact_number = fields.Char()
    email = fields.Char(string='Email Address')
    reason_ids = fields.Many2many('resignation.reason', string='Reason for Resignation')
    organization_rate_ids = fields.One2many('exit.interview.organization.rate', 'interview_id',
                                            default=lambda self: self.get_default_organization_rate())
    supervisor_rate_ids = fields.One2many('exit.interview.supervisor.rate', 'interview_id',
                                          default=lambda self: self.get_default_supervisor_rate())
    question_ids = fields.One2many('exit.interview.question', 'interview_id',
                                   default=lambda self: self.get_default_question())

    def get_default_organization_rate(self):
        vals = []
        for rate in self.env['organization.rate'].search([]):
            vals.append((0, 0, {'sequence': rate.sequence, 'name': rate.name}),)
        return vals

    def get_default_supervisor_rate(self):
        vals = []
        for rate in self.env['supervisor.rate'].search([]):
            vals.append((0, 0, {'sequence': rate.sequence, 'name': rate.name}),)
        return vals

    def get_default_question(self):
        vals = []
        for rate in self.env['interview.question'].search([]):
            vals.append((0, 0, {'sequence': rate.sequence, 'name': rate.name, 'yes_no': rate.yes_no}),)
        return vals
