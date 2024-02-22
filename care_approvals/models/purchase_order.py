from odoo import fields, models, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    approval_request_id = fields.Many2one('approval.request')

    def action_view_approval_request(self):
        return {
            'name': _('Approval Request'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'approval.request',
            'domain': [('id', '=', self.approval_request_id.id)],
            'target': 'current',
        }
