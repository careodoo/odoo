from odoo import fields, models, api, _
from datetime import datetime
from .qr_generator import generateQrCode
from odoo.http import request
from odoo.exceptions import ValidationError


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    def generate_barcode(self):
        return str(int(datetime.now().timestamp()))

    has_report = fields.Selection(related="category_id.has_report")
    barcode = fields.Char(default=generate_barcode)
    qr_image = fields.Binary("QR Code", compute='_generate_qr_code')
    qr_url = fields.Char("QR Code", compute='_generate_qr_code')
    department_id = fields.Many2one('hr.department')
    valid_department_ids = fields.Many2many('hr.department', compute='get_valid_department_ids')
    is_request_item = fields.Boolean()
    sale_order_ids = fields.One2many('sale.order', 'approval_request_id')
    so_count = fields.Integer(compute='compute_so_count')
    purchase_order_ids = fields.One2many('purchase.order', 'approval_request_id')
    po_count = fields.Integer(compute='compute_po_count')

    @api.model
    def default_get(self, fields):
        res = super(ApprovalRequest, self).default_get(fields)
        if self.env.context.get('default_is_request_item', False):
            category_id = self.env['approval.category'].search([('is_request_item', '=', True)], limit=1)
            if category_id:
                res['category_id'] = category_id.id
                res['request_owner_id'] = self.env.uid
                res['name'] = _('New')
        return res

    @api.model
    def create(self, vals):
        if vals.get('category_id', False):
            category_id = self.env['approval.category'].browse(vals['category_id'])
            if category_id.is_request_item:
                vals['name'] = self.env['ir.sequence'].next_by_code('request.item') or _('New')
        res = super(ApprovalRequest, self).create(vals)
        return res


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

    def button_create_po(self):
        return {
            'type': 'ir.actions.act_window',
            'name': "Create Purchase Order",
            'res_model': 'approval.request.order',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': self.id,
                'default_type': 'po',
            }
        }

    def button_create_so(self):
        return {
            'type': 'ir.actions.act_window',
            'name': "Create Sale Order",
            'res_model': 'approval.request.order',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': self.id,
                'default_type': 'so',
            }
        }

    @api.depends('sale_order_ids')
    def compute_so_count(self):
        for rec in self:
            rec.so_count = len(rec.sale_order_ids) if rec.sale_order_ids else 0

    def action_open_so(self):
        return {
            'type': 'ir.actions.act_window',
            'name': "Sale Orders",
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'domain': [('id', 'in', self.sale_order_ids.ids)]
        }

    @api.depends('purchase_order_ids')
    def compute_po_count(self):
        for rec in self:
            rec.po_count = len(rec.purchase_order_ids) if rec.purchase_order_ids else 0

    def action_open_po(self):
        return {
            'type': 'ir.actions.act_window',
            'name': "Purchase Orders",
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'domain': [('id', 'in', self.purchase_order_ids.ids)]
        }

    def print_report(self):
        return self.env.ref("care_approvals.action_approval_request_report").report_action(self)

    @api.depends('request_owner_id')
    def get_valid_department_ids(self):
      for approval in self:
        approval.valid_department_ids = False
        if approval.request_owner_id:
          valid_department_ids =  self.env['hr.department'].search([]).filtered(lambda dep: self.request_owner_id in dep.allowed_user_ids).mapped("parent_id")
          sub_department_ids = self.env['hr.department'].search([('parent_id','in',valid_department_ids.ids)])
          if valid_department_ids:
              approval.valid_department_ids =  (valid_department_ids | sub_department_ids).sorted(lambda dep:dep.display_name).ids
          else:
            approval.valid_department_ids =  self.request_owner_id.employee_ids.filtered(lambda e: e.department_id).mapped('department_id').ids
class ApprovalProductLine(models.Model):
    _inherit = 'approval.product.line'

    department_product_ids = fields.Many2many('product.product', compute='compute_department_product_ids', store=True)
    product_id = fields.Many2one('product.product', domain="[('id', 'in', department_product_ids)]")
    qoh_available = fields.Float(string="On Hand", compute='_compute_po_qoh')
    foh_available = fields.Float(string="Forecasted")
    request_uom_id = fields.Many2one('uom.uom')

    @api.constrains('quantity')
    def validate_quantity(self):
        for rec in self:
            if rec.quantity and rec.approval_request_id.department_id:
                lines = rec.approval_request_id.department_id.product_ids.filtered(lambda p: p.product_id.id == rec.product_id.id)
                if lines:
                    limit = lines[0].limit
                    if limit:
                        all_qty = sum(rec.approval_request_id.product_line_ids.filtered(lambda p: p.product_id.id == rec.product_id.id).mapped('quantity'))
                        if limit < all_qty:
                            raise ValidationError(f"you have exceeded limit for {rec.product_id.name} ({limit})!")

    @api.depends('product_id')
    def _compute_po_qoh(self):
        for rec in self:
            rec.qoh_available = rec.product_id.qty_available
            rec.foh_available = rec.product_id.virtual_available

    @api.depends('approval_request_id.department_id')
    def compute_department_product_ids(self):
        for rec in self:
            rec.department_product_ids = False
            if rec.approval_request_id.department_id:
                products = rec.approval_request_id.department_id.product_ids.mapped('product_id').mapped('id')
                rec.department_product_ids = [(6, 0, products)]
