from odoo import fields, models, api

CATEGORY_SELECTION = [
    ('required', 'Required'),
    ('optional', 'Optional'),
    ('no', 'None')]


class ApprovalCategory(models.Model):
    _inherit = 'approval.category'

    has_report = fields.Selection(CATEGORY_SELECTION, default="no", required=True)
    is_request_item = fields.Boolean()
