from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta


class PurchaseForecast(models.TransientModel):
    _name = 'purchase.forecast'
    _description = 'Purchase Forecast'

    line_ids = fields.One2many('purchase.forecast.line', 'wizard_id', string='Lines')
    date_start = fields.Date(string='Start', required=True)
    date_end = fields.Date(string='End', required=True)
    product_ids = fields.Many2many('product.product', string='Products')
    category_ids = fields.Many2many('product.category', string='Categories')
    state_ids = fields.Many2many('purchase.forecast.state', string='States')
    type = fields.Selection(selection=[
        ('day', 'Day'), ('month', 'Month')
    ], required=True)

    @api.constrains('date_start', 'date_end')
    def check_dates(self):
        for rec in self:
            if rec.date_start > rec.date_end:
                raise ValidationError("Start must be before End")

    def get_dates_between(self, date1, date2):
        my_list = []
        for n in range(int((date2 - date1).days) + 1):
            my_list.append(date1 + timedelta(n))
        return my_list

    def button_search(self):
        self.line_ids = [(5, 0, 0)]
        domain = []
        if self.state_ids:
            domain.append(('state', 'in', self.state_ids.mapped('type')))
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.mapped('id')))
        if self.category_ids:
            domain.append(('product_id.categ_id', 'in', self.category_ids.mapped('id')))
        lines_tuple = tuple(self.env['purchase.order.line'].sudo().search(domain).filtered(
            lambda p: self.date_start <= p.date_order.date() <= self.date_end
        ).mapped('id'))
        if lines_tuple:
            if len(lines_tuple) == 1:
                lines_tuple = tuple([lines_tuple[0], lines_tuple[0]])
            if self.type == 'day':
                query = f'''
                    SELECT forecast_date, product_id, count(id) AS count 
                    FROM purchase_order_line
                    WHERE id IN {lines_tuple} 
                    GROUP BY forecast_date, product_id; 
                '''
                self._cr.execute(query)
                lines = self._cr.dictfetchall()
                self.line_ids = [(0, 0, {
                    'date': line['forecast_date'],
                    'product_id': line['product_id'],
                    'total': line['count'],
                }) for line in lines]
            else:
                query = f'''
                    SELECT date_trunc('month', forecast_date) AS forecast_month, product_id, count(id) AS count 
                    FROM purchase_order_line
                    WHERE id IN {lines_tuple} 
                    GROUP BY forecast_month, product_id; 
                '''
                self._cr.execute(query)
                lines = self._cr.dictfetchall()
                self.line_ids = [(0, 0, {
                    'date': line['forecast_month'],
                    'product_id': line['product_id'],
                    'total': line['count'],
                }) for line in lines]
        else:
            raise UserError("Nothing found!")

        return {
            'type': 'ir.actions.act_window',
            'name': _('Forecast'),
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'purchase.forecast',
            'res_id': self.id,
            'target': 'new'
        }

    def print_xlsx(self):
        return self.env.ref('purchase_forecast.action_purchase_forecast_xlsx_report').report_action(self)


class PurchaseForecastLine(models.TransientModel):
    _name = 'purchase.forecast.line'
    _description = 'Purchase Forecast Line'
    _order = 'date'

    wizard_id = fields.Many2one('purchase.forecast')
    date = fields.Date()
    product_id = fields.Many2one('product.product')
    total = fields.Integer()


class PurchaseForecastState(models.Model):
    _name = 'purchase.forecast.state'
    _description = 'Purchase Forecast State'

    name = fields.Char()
    type = fields.Selection(selection=[
        ('draft', 'RFQ'), ('sent', 'RFQ Sent'), ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'), ('done', 'Locked'), ('cancel', 'Cancelled'), ('hold', 'Hold'),
        ('delayed', 'Delayed'), ('revised', 'Revised'), ('payment', 'Payment'),
        ('confirmed', 'Confirmed')
    ])
