from odoo import fields, models, api
from .qr import QrCodeGenerator
from odoo.http import request
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def get_default_sign_lines(self):
        return [(0, 0, {'employee_id': rec.employee_id.id}) for rec in self.env['default.sale.sign.employee'].search([])]

    department_id = fields.Many2one('hr.department', 'Department',
                                    domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    signature_lines = fields.One2many('sale.sign', 'sale_order_id', default=get_default_sign_lines)
    qr_image = fields.Binary("QR Code", compute='_generate_qr_code')
    qr_url = fields.Char("QR Code", compute='_generate_qr_code')
    cost_center_id = fields.Many2one('cost.center')
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
        for order in self:
            cost_center = order.cost_center_id
            if cost_center and order.date_order and cost_center.month_ids and order.state in ['sale', 'done']:
                month = False
                if cost_center.type == 'total' and cost_center.month_ids:
                    if cost_center.budget_start_date and cost_center.budget_end_date:
                        if cost_center.budget_start_date <= order.date_order.date() <= cost_center.budget_end_date:
                            month = cost_center.month_ids[0]
                elif cost_center.type == 'month':
                    month = cost_center.month_ids.filtered(lambda m: m.date.month == order.date_order.month and m.date.year == order.date_order.year)
                elif cost_center.type == 'annual':
                    month = cost_center.month_ids.filtered(lambda m: m.date.year == order.date_order.year)
                if not month:
                    raise ValidationError(f"Cost Center is not covering {order.date_order}!")
                if (month.used_budget + order.amount_total) > month.total_budget:
                    raise ValidationError("Used budget can't exceed total budget for {}!".format(month.date_string))
                month.used_budget += order.amount_total
                month.sale_order_ids = [(4, order.id)]
        return res

    def action_cancel(self):
        if self.state in ['sale', 'done'] and self.date_order and self.cost_center_id.month_ids:
            cost_center = self.cost_center_id
            month = False
            if cost_center.type == 'total' and cost_center.month_ids:
                if cost_center.budget_start_date and cost_center.budget_end_date:
                    if cost_center.budget_start_date <= self.date_order.date() <= cost_center.budget_end_date:
                        month = cost_center.month_ids[0]
            elif cost_center.type == 'month':
                month = cost_center.month_ids.filtered(lambda m: m.date.month == self.date_order.month and m.date.year == self.date_order.year)
            elif cost_center.type == 'annual':
                month = cost_center.month_ids.filtered(lambda m: m.date.year == self.date_order.year)
            if not month:
                raise ValidationError(f"Cost Center is not covering {self.date_order}!")
            month.used_budget -= self.amount_total
            month.sale_order_ids = [(3, self.id)]
        res = super(SaleOrder, self).action_cancel()
        return res
