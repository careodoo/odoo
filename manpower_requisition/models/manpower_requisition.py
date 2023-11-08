from odoo import fields, models, api
from .qr_generator import generateQrCode
from odoo.http import request
from datetime import datetime


class ManpowerRequisition(models.Model):
    _name = 'manpower.requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Manpower Requisition'

    def generate_barcode(self):
        return str(int(datetime.now().timestamp()))

    request_date = fields.Date(string='Date of Request')
    manager_id = fields.Many2one('hr.employee', string='Requesting Manager')
    location = fields.Char()
    required_title = fields.Char(string='Title of position required')
    requirement_number = fields.Integer(string='No of Requirements')
    type = fields.Selection(selection=[
        ('overseas', 'Overseas'), ('local', 'Local')
    ], required=True, string='Overseas / Local')
    # reasons
    leaving_employee_id = fields.Many2one('hr.employee', string='Employee Leaving')
    resignation_date = fields.Date(string='Resignation submitted on')
    transferred_employee_id = fields.Many2one('hr.employee', string='Employee being transferred')
    transfer_from = fields.Many2one('hr.department')
    transfer_to = fields.Many2one('hr.department')
    transfer_reason = fields.Char()
    project_id = fields.Many2one('project.project', string='Project Name')
    actual_headcount = fields.Integer()
    requirement_reason = fields.Text()
    specific_requirements = fields.Text()
    salary = fields.Float(string='Assigned salary for this requirements')
    working_hours = fields.Float()
    barcode = fields.Char(default=generate_barcode)
    qr_image = fields.Binary("QR Code", compute='_generate_qr_code')
    qr_url = fields.Char("QR Code", compute='_generate_qr_code')

    def _generate_qr_code(self):
        for rec in self:
            qr_info = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            action_id = self.env.ref('manpower_requisition.manpower_requisition_view_form').id
            menu_id = self.env.ref('manpower_requisition.manpower_requisition_menu').id
            qr_info += '/web#id=%s&action=%s&model=%s&view_type=form&cids=&menu_id=%s' % (rec.id, action_id, 'manpower.requisition', menu_id)
            rec.qr_url = qr_info
            rec.qr_image = generateQrCode.generate_qr_code(qr_info)
