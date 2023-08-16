from odoo import fields, models, api


class AccountAssetCategory(models.Model):
    _name = 'account.asset.category'
    _description = 'Account Asset Category'

    name = fields.Char(required=True)
