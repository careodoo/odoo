from odoo import models, fields, api, _

class RequestInvoice(models.Model):
    _name = 'request.invoice'
    _inherit = ['portal.mixin', 'product.catalog.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Request Invoice'

    name = fields.Char(string='Name',required=True, readonly=True, copy=False, default='/')
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    project_id = fields.Many2one('project.project', string='Project')
    department_id = fields.Many2one('hr.department', string='Department')
    invoice_date = fields.Date(string='Invoice Date')
    request_invoice_id = fields.One2many('request.invoice.line','request_id' ,string='Invoice Lines')
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    invoice_count = fields.Integer(string="Invoice Count", compute='_get_invoiced')
    invoice_ids = fields.Many2many(
        comodel_name='account.move',
        string="Invoices",
        compute='_get_invoiced',
        copy=False)
    state = fields.Selection(selection=[
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('invoiced', 'Invoiced'),
            ('rejected', 'Rejected'),
            ('cancel', 'Cancelled'),],string='Status',required=True,readonly=True,copy=False,tracking=True,default='draft')
    
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].get('request.invoice')
        return super(RequestInvoice, self).create(vals)
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.pricelist_id = self.partner_id.property_product_pricelist.id
    
    def action_draft(self):
        self.write({'state': 'draft'})

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_refuse(self):
        return {
            'name': _('Refuse Reason'),
            'type': 'ir.actions.act_window',
            'res_model': 'request.invoice.refusal.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': self.env.ref('care_request_invoice.request_invoice_refusal_wizard_view_form').id,
            'context': {
                'active_id': self.id,
                'refuse': True,
            }
        }
    
    def _action_refuse(self):
        self.write({'state': 'rejected'})

    @api.depends('invoice_date','request_invoice_id')
    def _get_invoiced(self):
        # The invoice_ids are obtained thanks to the invoice lines of the SO
        # lines, and we also search for possible refunds created directly from
        # existing invoices. This is necessary since such a refund is not
        # directly linked to the SO.
        for rec in self:
            invoices = self.env['account.move'].search([('request_invoice','=', rec.id)])
            rec.invoice_ids = invoices
            rec.invoice_count = len(invoices)

    def action_view_invoice(self, invoices=False):
        if not invoices:
            invoices = self.mapped('invoice_ids')
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_out_invoice_type')
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_move_type': 'out_invoice',
        }
        if len(self) == 1:
            context.update({
                'default_partner_id': self.partner_id.id,
                'default_invoice_origin': self.name,
            })
        action['context'] = context
        return action

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
        invoice_lines = []
        for line in self.request_invoice_id:
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
            if line.request_id.pricelist_id:
                pricelist_price, rule_id = self.env['product.pricelist'].search([('id','=',line.request_id.pricelist_id.id)])._get_product_price_rule(line.product_id,1)
                line.price = pricelist_price
                line.price_subtotal = pricelist_price * line.quantity
            else:
                line.price = line.product_id.lst_price
                line.price_subtotal = line.price * line.quantity

    