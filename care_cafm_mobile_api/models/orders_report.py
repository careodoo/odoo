# -*- coding: utf-8 -*-
from odoo import api, models


class ClientOrdersReport(models.AbstractModel):
    """Feeds the purchase-orders QWeb PDF: the controller passes the already
    computed rows/KPIs as ``data``; expose it so the template renders from it."""
    _name = 'report.care_cafm_mobile_api.report_client_orders'
    _description = 'تقرير طلبات الشراء (بيانات)'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {'doc_ids': docids, 'doc_model': 'sale.order', 'docs': [], 'data': data or {}}
