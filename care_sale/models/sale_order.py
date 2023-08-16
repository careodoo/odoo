from odoo import fields, models, api
from .qr import QrCodeGenerator
from odoo.http import request


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def get_default_sign_lines(self):
        return [(0, 0, {'employee_id': rec.employee_id.id}) for rec in self.env['default.sale.sign.employee'].search([])]

    department_id = fields.Many2one('hr.department', 'Department',
                                    domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    signature_lines = fields.One2many('sale.sign', 'sale_order_id', default=get_default_sign_lines)
    qr_image = fields.Binary("QR Code", compute='_generate_qr_code')
    qr_url = fields.Char("QR Code", compute='_generate_qr_code')
    # print options
    show_signature = fields.Boolean(default=True)
    show_terms = fields.Boolean(default=True)
    show_requestor = fields.Boolean(default=True)

    def _generate_qr_code(self):
        for rec in self:
            qr_info = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            qr_info += rec.get_portal_url()
            rec.qr_url = qr_info
            rec.qr_image = QrCodeGenerator.generate_qr_code(qr_info)

    def action_confirm(self):
        for order in self:
            order.signature_lines.filtered(lambda l: l.employee_id.user_id.id == self.env.uid).write({'confirm': True})
            if order.signature_lines.filtered(lambda l: not l.confirm):
                return
        res = super(SaleOrder, self).action_confirm()
        return res
