import pytz
from odoo import fields, models, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    forecast_date = fields.Date(compute='compute_forecast_date', store=True)

    @api.depends('order_id.date_order')
    def compute_forecast_date(self):
        for rec in self:
            if rec.order_id.date_order:
                timezone = pytz.timezone(self.env.user.tz or 'UTC')
                date_order = pytz.utc.localize(rec.order_id.date_order).astimezone(timezone)
                rec.forecast_date = date_order.date()
            else:
                rec.forecast_date = False
