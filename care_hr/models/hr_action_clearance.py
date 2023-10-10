from odoo import fields, models, api
from .qr_generator import generateQrCode
from odoo.http import request
from datetime import datetime


class HrActionClearance(models.Model):
    _name = 'hr.action.clearance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'
    _description = 'Hr Action Clearance'

    def get_default_lines(self):
        return [
            (0, 0, {'sequence': 1, 'name': 'Cash'}),
            (0, 0, {'sequence': 2, 'name': 'Stocks Products Balance - On hand'}),
            (0, 0, {'sequence': 3, 'name': 'Custody if any'}),
            (0, 0, {'sequence': 4, 'name': 'Staff Diabetes'}),
            (0, 0, {'sequence': 5, 'name': 'Any petty cash'}),
            (0, 0, {'sequence': 6, 'name': 'Disciplinary Action Pending'}),
            (0, 0, {'sequence': 7, 'name': 'ID / Email...ETC'}),
            (0, 0, {'sequence': 8, 'name': 'Insurance Card if any'}),
        ]

    def generate_barcode(self):
        return str(int(datetime.now().timestamp()))

    employee_id = fields.Many2one('hr.employee', required=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    image_1920 = fields.Image(related='employee_id.image_1920', store=True)
    barcode = fields.Char(default=generate_barcode)
    qr_image = fields.Binary("QR Code", compute='_generate_qr_code')
    qr_url = fields.Char("QR Code", compute='_generate_qr_code')
    employee_barcode = fields.Char(related='employee_id.barcode', store=True)
    line_ids = fields.One2many('hr.action.clearance.line', 'clearance_id', default=get_default_lines)
    state = fields.Selection(selection=[
        ('draft', 'Draft'), ('submit', 'Submitted'), ('approved', 'Approved'),
    ], default='draft')

    def button_submit(self):
        self.state = 'submit'
        self.barcode = str(int(datetime.now().timestamp()))

    def button_approve(self):
        self.state = 'approved'

    def _generate_qr_code(self):
        for rec in self:
            qr_info = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            action_id = self.env.ref('care_hr.clearance_view_form').id
            menu_id = self.env.ref('care_hr.clearance_menu').id
            qr_info += '/web#id=%s&action=%s&model=%s&view_type=form&cids=&menu_id=%s' % (rec.id, action_id, 'hr.action.clearance', menu_id)
            rec.qr_url = qr_info
            rec.qr_image = generateQrCode.generate_qr_code(qr_info)


class HrActionClearanceLine(models.Model):
    _name = 'hr.action.clearance.line'
    _description = 'Hr Action Clearance Line'
    _order = 'sequence'

    clearance_id = fields.Many2one('hr.action.clearance')
    name = fields.Char()
    remarks = fields.Char()
    sequence = fields.Integer()
