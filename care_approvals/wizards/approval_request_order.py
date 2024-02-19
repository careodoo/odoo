from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ApprovalRequestOrder(models.TransientModel):
    _name = 'approval.request.order'
    _description = 'Approval Request Order'

    request_id = fields.Many2one('approval.request')
    type = fields.Selection(selection=[
        ('so', 'Sale Order'), ('po', 'Purchase Order')
    ], required=True)
    line_ids = fields.One2many('approval.request.order.line', 'wizard_id')

    @api.onchange('request_id')
    def onchange_request_id(self):
        if self.request_id:
            line_ids = [(5, 0, 0)]
            line_fields = [f for f in self.env['approval.request.order.line']._fields.keys()]
            line_ids_data_tmpl = self.env['approval.request.order'].default_get(line_fields)
            for line in self.request_id.product_line_ids:
                line_ids_data = dict(line_ids_data_tmpl)
                line_ids_data.update(self._prepare_line_vals(line))
                line_ids.append((0, 0, line_ids_data))
            self.update({
                'line_ids': line_ids,
            })

    @api.model
    def _prepare_line_vals(self, line):
        return {
            'product_line_id': line.id,
            'quantity': line.quantity,
        }

    def button_create_so(self):
        vals = []
        for line in self.line_ids:
            if line.quantity > line.product_line_id.quantity:
                raise ValidationError(f"{line.product_id.name} quantity can't exceed request quantity")
            vals.append((0, 0, {
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
            }))
        self.env['sale.order'].create({
            'partner_id': self.request_id.request_owner_id.partner_id.id,
            'department_id': self.request_id.department_id.id,
            'approval_request_id': self.request_id.id,
            'order_line': vals
        })

    def button_create_po(self):
        vals = []
        for line in self.line_ids:
            if line.quantity > line.product_line_id.quantity:
                raise ValidationError(f"{line.product_id.name} quantity can't exceed request quantity")
            vals.append((0, 0, {
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
            }))
        self.env['purchase.order'].create({
            'partner_id': self.request_id.request_owner_id.partner_id.id,
            'department_id': self.request_id.department_id.id,
            'approval_request_id': self.request_id.id,
            'order_line': vals
        })


class POApprovalRequestLine(models.TransientModel):
    _name = 'approval.request.order.line'
    _description = 'PO Approval Request Line'

    wizard_id = fields.Many2one('approval.request.order')
    product_line_id = fields.Many2one('approval.product.line')
    product_id = fields.Many2one('product.product', related='product_line_id.product_id', store=True)
    description = fields.Char(related='product_line_id.description')
    quantity = fields.Float()
    product_uom_id = fields.Many2one('uom.uom', related='product_line_id.product_uom_id')
