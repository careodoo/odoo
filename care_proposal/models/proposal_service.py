from odoo import fields, models, api, _


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

    # --- Customer Cost Books (per-customer, dated, snapshot-able) ---------
    cost_book_ids = fields.One2many(
        'proposal.service.cost', 'service_id', string='Cost Books')
    cost_book_count = fields.Integer(
        compute='_compute_cost_book_count', string='Cost Books')

    def _compute_cost_book_count(self):
        for rec in self:
            rec.cost_book_count = len(rec.cost_book_ids)

    def get_service_item_cost(self, type):
        item = self.line_ids.filtered(lambda l: l.type == type)
        return item.cost if item else 0

    def get_cost_book(self, partner=None, date=None):
        """Return the applicable ACTIVE cost book for a customer on a date.

        Resolution order: a customer-specific active book whose effective_date
        is on/before ``date`` (latest wins); otherwise the latest active
        DEFAULT book (no partner). Returns an empty recordset if none exists,
        in which case callers fall back to the legacy service line cost."""
        self.ensure_one()
        date = date or fields.Date.context_today(self)
        Book = self.env['proposal.service.cost']
        base = [('service_id', '=', self.id), ('state', '=', 'active'),
                ('effective_date', '<=', date)]
        if partner:
            book = Book.search(
                base + [('partner_id', '=', partner.id)],
                order='effective_date desc', limit=1)
            if book:
                return book
        return Book.search(
            base + [('partner_id', '=', False)],
            order='effective_date desc', limit=1)

    def action_view_cost_books(self):
        self.ensure_one()
        return {
            'name': _('Cost Books'),
            'type': 'ir.actions.act_window',
            'res_model': 'proposal.service.cost',
            'view_mode': 'tree,form',
            'domain': [('service_id', '=', self.id)],
            'context': {'default_service_id': self.id},
        }

    @api.depends('line_ids.cost')
    def compute_total_cost(self):
        for rec in self:
            rec.total_cost = 0
            if rec.line_ids:
                rec.total_cost = sum(rec.line_ids.mapped('cost'))


