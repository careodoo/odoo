from odoo import fields, models, api
from datetime import datetime
from .qr_generator import generateQrCode
from odoo.http import request


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    def generate_barcode(self):
        return str(int(datetime.now().timestamp()))

    has_report = fields.Selection(related="category_id.has_report")
    barcode = fields.Char(default=generate_barcode)
    qr_image = fields.Binary("QR Code", compute='_generate_qr_code')
    qr_url = fields.Char("QR Code", compute='_generate_qr_code')
    department_id = fields.Many2one('hr.department', compute='compute_department_id')

    @api.depends('request_owner_id')
    def compute_department_id(self):
        for rec in self:
            rec.department_id = False
            if rec.request_owner_id:
                departments = rec.request_owner_id.employee_ids.filtered(lambda e: e.department_id).mapped('department_id')
                if departments:
                    rec.department_id = departments[0].id

    def _generate_qr_code(self):
        for rec in self:
            qr_info = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            menu_id = self.env.ref('approvals.approvals_menu_root').id
            qr_info += '/web#id=%s&model=%s&view_type=form&cids=&menu_id=%s' % (rec.id, 'approval.request', menu_id)
            rec.qr_url = qr_info
            rec.qr_image = generateQrCode.generate_qr_code(qr_info)

    def print_report(self):
        return self.env.ref("care_approvals.action_approval_request_report").report_action(self)
