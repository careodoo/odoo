from odoo import api, fields, models, _


class ProposalServiceCost(models.Model):
    """Customer Cost Book — the cost of a service FOR A CUSTOMER, on a date.

    Solves two problems at once:
      * the SAME service can cost differently per customer (partner_id), and
      * costs are versioned by effective_date, so a proposal can freeze the
        book that applied when it was created and never drift afterwards.

    A book with no partner is the DEFAULT book (fallback for any customer)."""

    _name = 'proposal.service.cost'
    _description = 'Service Cost Book'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'service_id, partner_id, effective_date desc, id desc'

    service_id = fields.Many2one(
        'proposal.service', string='Service', required=True,
        ondelete='cascade', index=True, tracking=True)
    partner_id = fields.Many2one(
        'res.partner', string='Customer', tracking=True,
        help="Leave empty for the DEFAULT cost book used for any customer.")
    is_default = fields.Boolean(
        string='Default book', compute='_compute_is_default', store=True)
    effective_date = fields.Date(
        required=True, default=fields.Date.context_today, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
    ], default='draft', required=True, tracking=True, copy=False)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', tracking=True,
        default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, tracking=True)
    line_ids = fields.One2many(
        'proposal.service.cost.line', 'cost_id', string='Components')
    total_cost = fields.Monetary(
        compute='_compute_total_cost', store=True, currency_field='currency_id', tracking=True)
    note = fields.Char(tracking=True)
    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('partner_id')
    def _compute_is_default(self):
        for rec in self:
            rec.is_default = not rec.partner_id

    @api.depends('line_ids.amount')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = sum(rec.line_ids.mapped('amount'))

    @api.depends('service_id', 'partner_id', 'effective_date')
    def _compute_display_name(self):
        for rec in self:
            who = rec.partner_id.name or _('Default')
            svc = rec.service_id.name or ''
            rec.display_name = "%s · %s · %s" % (svc, who, rec.effective_date or '')

    def action_activate(self):
        """Activate this book and archive any other active book for the same
        (service, customer) so there is exactly one active book at a time."""
        for rec in self:
            others = self.search([
                ('service_id', '=', rec.service_id.id),
                ('partner_id', '=', rec.partner_id.id),
                ('state', '=', 'active'),
                ('id', '!=', rec.id),
            ])
            others.write({'state': 'archived'})
            rec.state = 'active'
        return True

    def action_archive_book(self):
        self.write({'state': 'archived'})

    def action_draft(self):
        self.write({'state': 'draft'})


class ProposalServiceCostLine(models.Model):
    _name = 'proposal.service.cost.line'
    _description = 'Service Cost Book Line'
    _order = 'sequence, id'

    cost_id = fields.Many2one(
        'proposal.service.cost', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    component_id = fields.Many2one(
        'proposal.cost.component', string='Component', required=True)
    amount = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(related='cost_id.currency_id', store=True)
    note = fields.Char()
