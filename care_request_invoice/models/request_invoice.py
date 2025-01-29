from odoo import models, fields, api

class RequestInvoice(models.Model):
    _name = 'request.invoice'
    _inherit = ['portal.mixin', 'product.catalog.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Request Invoice'

    name = fields.Char(string='Name',required=True, readonly=True, copy=False, default='/')
    partner_id = fields.Many2one('res.partner', string='Customer')
    project_id = fields.Many2one('project.project', string='Project')
    department_id = fields.Many2one('hr.department', string='Department')
    invoice_date = fields.Date(string='Invoice Date')
    request_invoice_id = fields.One2many('request.invoice.line','request_id' ,string='Invoice Lines')
    state = fields.Selection(selection=[
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('invoiced', 'Invoiced'),
            ('cancel', 'Cancelled'),],string='Status',required=True,readonly=True,copy=False,tracking=True,default='draft')
    
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].get('request.invoice')
        return super(RequestInvoice, self).create(vals)

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_convert_to_invoice(self):
        invoice = self.env['account.move'].create({
            'request_invoice': self.id,
            'partner_id': self.partner_id.id,
            'project_id': self.project_id.id,
            'department_id': self.department_id.id,
            'invoice_payment_term_id': self.partner_id.property_payment_term_id.id,
            'journal_id': self.env['account.journal'].search([('type','=','sale')]).id,
            'move_type': 'out_invoice',
            'invoice_date': self.invoice_date,
        })
        invoice
        print(invoice)
        invoice_lines = []
        for line in self.request_invoice_id:
            print('line')
            print(line)
            invoice_lines.append((0, 0, {
            'move_id': invoice.id,
            'product_id': line.product_id.id,
            'quantity': line.quantity,
            'price_unit': line.price,
            'name': line.label,
            'display_type': 'product',
            'product_uom_id': line.product_uom_id.id,
        }))
        invoice.write({'invoice_line_ids': invoice_lines})
        print(invoice)
        print(invoice.invoice_line_ids)
        self.write({'state': 'invoiced'})


class RequestInvoiceLine(models.Model):
    _name = 'request.invoice.line'
    _description = 'Request Invoice Line'

    request_id = fields.Many2one('request.invoice', string='Invoice Request')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    display_type = fields.Selection(selection=[('product', 'Product')],default='product', store=True, readonly=False,required=True, compute="_compute_name")
    label = fields.Char(string='Label', compute="_compute_name")
    quantity = fields.Integer(string='Quantity', default=1.0)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=False,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Account Currency', related='company_id.currency_id')
    price = fields.Float(string='Price', default=0.0, compute="_compute_total")
    price_subtotal = fields.Monetary(string='Tax excl.', default=0.0, compute="_compute_total")

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.product_uom_id = False
        self.display_type = 'product'
        for line in self:
            if line.product_id:
                line.product_uom_id = line.product_id.uom_id
                line.price = line.product_id.lst_price
                line.display_type = 'product'

    @api.depends('product_id')
    def _compute_name(self):
        self.label = ''
        for line in self:
            values = []
            if line.product_id.partner_ref:
                values.append(line.product_id.partner_ref)
            if line.product_id.description_sale:
                values.append(line.product_id.description_sale)
            
            line.label = '\n'.join(values)

    @api.depends('product_id','quantity')
    def _compute_total(self):
        self.price = 0.0
        self.price_subtotal = 0.0
        for line in self:
            line.price = line.product_id.lst_price
            line.price_subtotal = line.price * line.quantity

    