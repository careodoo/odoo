from odoo import _, api, fields, models

class ServiceTripXlsxReport(models.AbstractModel):
  _name = 'report.service_order.service_trip_report'
  _description = 'Service Trip Xlsx Report'

  @api.model
  def _get_report_values(self, docids, data):
    return {
        'doc_ids': docids,
        'doc_model': 'service.trip',
        'docs': self.env['service.trip'].browse(docids),
    }