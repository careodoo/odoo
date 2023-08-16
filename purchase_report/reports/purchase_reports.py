from odoo import fields, models, api, _
from odoo.exceptions import UserError


class PurchaseReport(models.AbstractModel):
    _name = 'report.purchase.report_purchaseorder'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['purchase.order'].browse(docids)
        for doc in docs:
            if doc.state not in ['purchase', 'done'] and self.env.uid not in doc.signature_lines.mapped('employee_id').mapped('user_id').ids:
                raise UserError("you can't print report in {} state".format(doc.state))
        return {
            'doc_ids': docs.ids,
            'doc_model': 'purchase.order',
            'docs': docs,
        }


class PurchaseHeaderReport(models.AbstractModel):
    _name = 'report.purchase_report.report_purchaseorder_header'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['purchase.order'].browse(docids)
        for doc in docs:
            if doc.state not in ['purchase', 'done'] and self.env.uid not in doc.signature_lines.mapped('employee_id').mapped('user_id').ids:
                raise UserError("you can't print report in {} state".format(doc.state))
        return {
            'doc_ids': docs.ids,
            'doc_model': 'purchase.order',
            'docs': docs,
        }
