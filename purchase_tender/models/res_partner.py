from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    tender_group_id = fields.Many2one(
        'res.partner', string='مجموعة المنافس / المالك',
        domain="[('id','!=',id)]",
        help="Link sister companies under one owner/group so competitor analysis consolidates them.")
    tender_is_competitor = fields.Boolean(
        string='منافس مُتابَع',
        help="Mark this partner as a tracked competitor (watchlist).")
