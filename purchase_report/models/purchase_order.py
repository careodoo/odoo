from odoo import fields, models, api
from .qr import QrCodeGenerator
from odoo.http import request


class PurchaseInherit(models.Model):
    _inherit = 'purchase.order'

    def get_default_sign_lines(self):
        default_employees = []
        IPC = self.env['ir.config_parameter'].sudo()
        sign_1 = IPC.get_param('purchase_report.sign_employee_1')
        if sign_1:
            default_employees.append((0, 0, {'employee_id': self.env['hr.employee'].browse(int(sign_1)).id}))
        sign_2 = IPC.get_param('purchase_report.sign_employee_2')
        if sign_2:
            default_employees.append((0, 0, {'employee_id': self.env['hr.employee'].browse(int(sign_2)).id}))
        sign_3 = IPC.get_param('purchase_report.sign_employee_3')
        if sign_3:
            default_employees.append((0, 0, {'employee_id': self.env['hr.employee'].browse(int(sign_3)).id}))

        return default_employees

    department_id = fields.Many2one('hr.department', 'Department',
                                    domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    request_id = fields.Many2one('purchase.request')
    signature_lines = fields.One2many('purchase.sign', 'purchase_order_id', default=get_default_sign_lines)
    cost_center_id = fields.Many2one('cost.center')
    qr_image = fields.Binary("QR Code", compute='_generate_qr_code')
    qr_url = fields.Char("QR Code", compute='_generate_qr_code')
    amount_total = fields.Monetary(digits=(16, 3))
    state = fields.Selection(selection_add=[
        ('hold', 'Hold'),
        ('delayed', 'Delayed'),
        ('revised', 'Revised'),
        ('payment', 'Payment'),
        ('confirmed', 'Confirmed'),
    ])
    # print options
    show_signature = fields.Boolean(default=True)
    show_terms = fields.Boolean(default=True)
    show_requestor = fields.Boolean(default=True)

    def button_hold(self):
        for order in self:
            order.state = 'hold'

    def button_delay(self):
        for order in self:
            order.state = 'delayed'

    def button_revised(self):
        for order in self:
            order.state = 'revised'

    def button_payment(self):
        for order in self:
            order.state = 'payment'

    def button_confirmed_state(self):
        for order in self:
            order.state = 'confirmed'

    def button_confirm(self):
        for order in self:
            order.signature_lines.filtered(lambda l: l.employee_id.user_id.id == self.env.uid).write({'confirm': True})
            if order.signature_lines.filtered(lambda l: not l.confirm):
                return
        res = super(PurchaseInherit, self).button_confirm()
        return res

    @api.depends('company_id')
    def _generate_qr_code(self):
        for rec in self:
            qr_info = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            qr_info += rec.get_portal_url()
            rec.qr_url = qr_info
            rec.qr_image = QrCodeGenerator.generate_qr_code(qr_info)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    price_unit = fields.Float(digits=(16, 3))
    price_subtotal = fields.Monetary(digits=(16, 3))