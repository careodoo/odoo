from odoo import fields, models, api


class ProposalService(models.Model):
    _name = 'proposal.service'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Proposal Service'

    name = fields.Char(required=True)
    type = fields.Selection(
        selection=[
            ('manpower', 'Manpower'),
            ('service', 'Service'),
        ],
        required=True,
        default='manpower',
    )
    short_code = fields.Char(required=True)
    daily_hours = fields.Integer()
    weekly_days = fields.Integer()
    monthly_days = fields.Integer()
    total_cost = fields.Float(compute='compute_total_cost', store=True,)
    line_ids = fields.One2many('proposal.service.item', 'proposal_service_id',)

    def get_service_item_cost(self, type):
        item = self.line_ids.filtered(lambda l: l.type == type)
        return item.cost if item else 0

    @api.depends('line_ids.cost')
    def compute_total_cost(self):
        for rec in self:
            rec.total_cost = 0
            if rec.line_ids:
                rec.total_cost = sum(rec.line_ids.mapped('cost'))


