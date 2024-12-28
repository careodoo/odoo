import pytz
from datetime import datetime
from odoo import _, api, fields, models


class ServiceOrderReport(models.AbstractModel):
    _name = 'report.service_order.service_order_report'
    _description = 'Service Order Report'

    def get_timezone_offset(self):
        tz = self.env.user.tz
        offset = 2
        if tz:
            timezone = pytz.timezone(tz)
            aware1 = timezone.localize(datetime.now())
            offset = aware1.utcoffset().seconds / 3600
        return offset

    @api.model
    def _get_report_values(self, docids, data):
        return {
            'doc_ids': docids,
            'doc_model': 'service.order',
            'docs': self.env['service.order'].browse(docids),
            'timzone_offset': self.get_timezone_offset(),
        }
