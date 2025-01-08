from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ApprovalRequestOrder(models.TransientModel):
    _name = 'approval.request.order'
    _description = 'Approval Request Order'

    request_id = fields.Many2one('approval.request')
    type = fields.Selection(selection=[
        ('so', 'Sale Order'), ('po', 'Purchase Order')
    ], required=True)
    product_ids = fields.Many2many('approval.product.line')
    partner_id = fields.Many2one('res.partner', required=True)
    department_id = fields.Many2one('hr.department')

    def button_create_so(self):
        vals = []
        for line in self.product_ids:
            vals.append((0, 0, {
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.request_uom_id.id if line.request_uom_id else line.product_uom_id.id,
            }))
        if vals:
            request_id = self.product_ids[0].approval_request_id
            self.env['sale.order'].create({
                'partner_id': self.partner_id.id,
                'department_id': self.department_id.id,
                'approval_request_id': request_id.id,
                'order_line': vals
            })
            return {'type': 'ir.actions.client', 'tag': 'reload'}

    def button_create_po(self):
        vals = []
        for line in self.product_ids:
            vals.append((0, 0, {
                'product_id': line.product_id.id,
                'product_qty': line.quantity,
                'product_uom': line.request_uom_id.id if line.request_uom_id else line.product_uom_id.id,
            }))
        if vals:
            request_id = self.product_ids[0].approval_request_id
            self.env['purchase.order'].create({
                'partner_id': self.partner_id.id,
                'department_id': self.department_id.id,
                'approval_request_id': request_id.id,
                'order_line': vals
            })
            return {'type': 'ir.actions.client', 'tag': 'reload'}
