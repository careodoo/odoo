# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class CafmCatalogItem(models.Model):
    """Approved catalogue item the client can order (cleaning supplies, tools…)."""
    _name = 'care.cafm.catalog.item'
    _description = 'CAFM Catalog Item'
    _order = 'category, name'

    name = fields.Char(string='الصنف', required=True, translate=True)
    product_id = fields.Many2one('product.product', string='المنتج (Odoo)',
                                 help='الربط بمنتج Odoo لتحويل الطلب لأمر بيع/شراء.')
    category = fields.Char(string='الفئة')
    uom_name = fields.Char(string='الوحدة', default='قطعة')
    price = fields.Float(string='السعر')
    icon = fields.Char(default='📦')
    active = fields.Boolean(default=True)


class CafmRequest(models.Model):
    """A client purchase request from the catalog. Convert to a Sale Order (we
    supply) or a Purchase Order (we buy from a supplier), then track to delivery
    and issuance."""
    _name = 'care.cafm.request'
    _description = 'CAFM Client Purchase Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True, tracking=True)
    partner_id = fields.Many2one(related='facility_id.partner_id', store=True, string='العميل')
    project_id = fields.Many2one(related='facility_id.project_id', store=True)
    requested_by = fields.Many2one('res.users', string='مقدّم الطلب', default=lambda s: s.env.user)
    supplier_id = fields.Many2one('res.partner', string='المورّد (لطلب الشراء)')
    date = fields.Date(string='التاريخ', default=fields.Date.context_today, required=True)
    state = fields.Selection([
        ('draft', 'مسودة'), ('submitted', 'مُقدَّم'), ('approved', 'معتمد'),
        ('ordered', 'أمر بيع/شراء'), ('delivered', 'مورّد لمخزن العميل'),
        ('issued', 'قيد الصرف'), ('done', 'مكتمل'), ('cancelled', 'ملغى'),
    ], default='draft', tracking=True)
    line_ids = fields.One2many('care.cafm.request.line', 'request_id', string='الأصناف')
    amount_total = fields.Float(string='الإجمالي', compute='_compute_total', store=True)
    line_count = fields.Integer(compute='_compute_total')
    sale_order_id = fields.Many2one('sale.order', string='أمر البيع', readonly=True, copy=False)
    purchase_order_id = fields.Many2one('purchase.order', string='أمر الشراء', readonly=True, copy=False)
    note = fields.Text()
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('line_ids', 'line_ids.subtotal')
    def _compute_total(self):
        for r in self:
            r.amount_total = sum(r.line_ids.mapped('subtotal'))
            r.line_count = len(r.line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', '/') == '/':
                v['name'] = self.env['ir.sequence'].next_by_code('care.cafm.request') or '/'
        return super().create(vals_list)

    def action_submit(self):
        for r in self:
            if not r.line_ids:
                raise UserError(_('أضف أصنافاً للطلب أولاً.'))
            r.state = 'submitted'

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_create_sale_order(self):
        self.ensure_one()
        if 'sale.order' not in self.env:
            raise UserError(_('وحدة المبيعات غير مثبّتة.'))
        if not self.partner_id:
            raise UserError(_('المرفق غير مرتبط بعميل.'))
        lines = []
        for l in self.line_ids:
            if not l.product_id:
                raise UserError(_('الصنف «%s» غير مرتبط بمنتج Odoo.') % l.name)
            lines.append((0, 0, {'product_id': l.product_id.id, 'product_uom_qty': l.qty,
                                 'price_unit': l.price, 'name': l.name}))
        so = self.env['sale.order'].create({'partner_id': self.partner_id.id, 'order_line': lines})
        self.write({'sale_order_id': so.id, 'state': 'ordered'})
        self.message_post(body=_('تم إنشاء أمر بيع %s.') % so.name)
        return {'type': 'ir.actions.act_window', 'res_model': 'sale.order', 'res_id': so.id, 'view_mode': 'form'}

    def action_create_purchase(self):
        self.ensure_one()
        if 'purchase.order' not in self.env:
            raise UserError(_('وحدة المشتريات غير مثبّتة.'))
        if not self.supplier_id:
            raise UserError(_('حدّد المورّد أولاً.'))
        lines = []
        for l in self.line_ids:
            if not l.product_id:
                raise UserError(_('الصنف «%s» غير مرتبط بمنتج Odoo.') % l.name)
            lines.append((0, 0, {'product_id': l.product_id.id, 'product_qty': l.qty,
                                 'price_unit': l.price, 'name': l.name,
                                 'date_planned': fields.Datetime.now(),
                                 'product_uom': l.product_id.uom_po_id.id}))
        po = self.env['purchase.order'].create({'partner_id': self.supplier_id.id, 'order_line': lines})
        self.write({'purchase_order_id': po.id, 'state': 'ordered'})
        self.message_post(body=_('تم إنشاء أمر شراء %s.') % po.name)
        return {'type': 'ir.actions.act_window', 'res_model': 'purchase.order', 'res_id': po.id, 'view_mode': 'form'}

    def action_delivered(self):
        self.write({'state': 'delivered'})

    def action_issue(self):
        self.write({'state': 'issued'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_print(self):
        return self.env.ref('care_cafm_procurement.action_report_request').report_action(self)


class CafmRequestLine(models.Model):
    _name = 'care.cafm.request.line'
    _description = 'CAFM Request Line'
    _order = 'id'

    request_id = fields.Many2one('care.cafm.request', required=True, ondelete='cascade')
    item_id = fields.Many2one('care.cafm.catalog.item', string='من الكتالوج')
    product_id = fields.Many2one('product.product', string='المنتج')
    name = fields.Char(string='الصنف', required=True)
    qty = fields.Float(string='الكمية', default=1.0)
    uom_name = fields.Char(string='الوحدة')
    price = fields.Float(string='السعر')
    subtotal = fields.Float(compute='_compute_sub', store=True)
    qty_received = fields.Float(string='المستلَم')
    qty_issued = fields.Float(string='المصروف')

    @api.depends('qty', 'price')
    def _compute_sub(self):
        for l in self:
            l.subtotal = (l.qty or 0.0) * (l.price or 0.0)

    @api.onchange('item_id')
    def _onchange_item(self):
        if self.item_id:
            self.name = self.item_id.name
            self.product_id = self.item_id.product_id
            self.uom_name = self.item_id.uom_name
            self.price = self.item_id.price
