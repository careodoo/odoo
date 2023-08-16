from odoo import fields, models, api


class PurchaseSign(models.Model):
    _inherit = 'purchase.sign'

    asset_transfer_id = fields.Many2one('asset.transfer')

    @api.depends('purchase_order_id', 'request_id', 'extra_budget_id', 'asset_transfer_id')
    def compute_rec_name(self):
        for rec in self:
            rec.rec_name = ''
            if rec.purchase_order_id:
                rec.rec_name = 'Ask to Sign PO {}'.format(rec.purchase_order_id.name)
            elif rec.request_id:
                rec.rec_name = 'Ask to Sign PR {}'.format(rec.request_id.name)
            elif rec.asset_transfer_id:
                rec.rec_name = 'Ask to Sign Asset Transfer {}'.format(rec.asset_transfer_id.asset_id.name)
            elif rec.extra_budget_id:
                rec.rec_name = 'Ask to Sign Extra Budget for Cost Center {} for {}'.format(
                    rec.extra_budget_id.cost_center_id.name, rec.extra_budget_id.month_id.date_string
                )

