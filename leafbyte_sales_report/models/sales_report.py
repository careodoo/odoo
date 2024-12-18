
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SalesReport(models.Model):
    _name = 'sales.report'
    _description = 'Sales Report'

    name = fields.Char('Name')

    # Main Fields
    company_id = fields.Many2one('res.company')
    date_order = fields.Datetime('Datetime')
    partner_id = fields.Many2one('res.partner')
    product_id = fields.Many2one('product.product')
    qty = fields.Float()
    uom_id = fields.Many2one('uom.uom')
    price_unit = fields.Float()
    price_tax = fields.Float()
    tax_id = fields.Many2many('account.tax')
    subtotal = fields.Float()
    total = fields.Float()

    sale_order_id = fields.Many2one('sale.order')
    pos_order_id = fields.Many2one('pos.order')

    def get_view(self, view_id=None, view_type='tree', **options):
        res = super(SalesReport, self).get_view(view_id, view_type, **options)
        self.fetch_sales_data()
        return res

    def fetch_sales_data(self):
        # cleaning data
        sales_report = self.env['sales.report'].search([]).unlink()

        # sale order
        sale_order_line = self.env['sale.order.line'].search([('state','=','sale')])
        if sale_order_line:
            for line in sale_order_line:
                sales_report_sol = self.env['sales.report'].create({
                    'company_id': line.company_id.id,
                    'name': "(" + line.order_id.name + ") " + line.product_id.name,
                    'date_order': line.order_id.date_order,
                    'partner_id': line.order_id.partner_id.id,
                    'product_id': line.product_id.id,
                    'qty': line.product_uom_qty,
                    'uom_id': line.product_uom.id,
                    'price_unit': line.price_unit,
                    'price_tax': line.price_tax,
                    'tax_id': line.tax_id.ids,
                    'subtotal': line.price_subtotal,
                    'total': line.price_total,
                    'sale_order_id' : line.order_id.id
                })

        # POS
        pos_order_line = self.env['pos.order.line'].search([])
        if pos_order_line:
            for pline in pos_order_line:
                sales_report_posl = self.env['sales.report'].create({
                    'company_id': pline.order_id.company_id.id,
                    'name': "(" + pline.order_id.name + ") " + pline.product_id.name,
                    'date_order': pline.order_id.date_order,
                    'partner_id': pline.order_id.partner_id.id,
                    'product_id': pline.product_id.id,
                    'qty': pline.qty,
                    'uom_id': pline.product_uom_id.id,
                    'price_unit': pline.price_unit                ,
                    'price_tax': (pline.price_subtotal_incl - pline.price_subtotal),
                    'tax_id': pline.tax_ids_after_fiscal_position.ids,
                    'subtotal': pline.price_subtotal,
                    'total': pline.price_subtotal_incl,
                    'pos_order_id' : pline.order_id.id
                })