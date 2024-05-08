from odoo import fields, models, api
from .qr_generator import generateQrCode
from odoo.http import request
from datetime import datetime


class ExitInterview(models.Model):
    _name = 'exit.interview'
    _description = 'Exit Interview'

    def generate_barcode(self):
        return str(int(datetime.now().timestamp()))

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
    barcode = fields.Char(default=generate_barcode)
    qr_image = fields.Binary("QR Code", compute='_generate_qr_code')
    qr_url = fields.Char("QR Code", compute='_generate_qr_code')
    active = fields.Boolean(default=True)

    def _generate_qr_code(self):
        for rec in self:
            qr_info = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            action_id = self.env.ref('exit_interview.exit_interview_action').id
            menu_id = self.env.ref('exit_interview.exit_interview_menu').id
            qr_info += '/web#id=%s&action=%s&model=%s&view_type=form&cids=&menu_id=%s' % (rec.id, action_id, 'exit.interview', menu_id)
            rec.qr_url = qr_info
            rec.qr_image = generateQrCode.generate_qr_code(qr_info)

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
