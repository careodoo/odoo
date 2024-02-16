from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ScrapReport(models.TransientModel):
    _name = 'scrap.report'
    _description = 'Scrap Report'

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    order_ids = fields.Many2many('stock.scrap')

    @api.constrains('date_from', 'date_to')
    def check_start_end_date(self):
        if self.date_to < self.date_from:
            raise ValidationError(_('End Date should be greater than Start Date.'))

    def print_report(self):
        orders = self.env['stock.scrap'].search([]).filtered(
            lambda s: self.date_from < s.date_done.date() < self.date_to
        )
        self.order_ids = [(6, 0, orders.ids)]
        return self.env.ref('care_stock.action_scrap_report').report_action(self)
