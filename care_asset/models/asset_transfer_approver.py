from odoo import fields, models, api


class AssetTransferApprover(models.Model):
    _name = 'asset.transfer.approver'
    _description = 'Asset Transfer Approver'

    user_id = fields.Many2one('res.users', required=True)
