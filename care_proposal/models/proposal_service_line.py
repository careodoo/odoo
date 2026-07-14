from odoo import _, api, fields, models


class ProposalServiceLine(models.Model):
    _name = 'proposal.service.line'
    _rec_name = 'proposal_service_id'
    _description = 'Proposal Service Line'

    proposal_id = fields.Many2one('proposal.proposal')
    proposal_service_id = fields.Many2one('proposal.service', required=True, string='Service')
    location_id = fields.Many2one('proposal.service.location')
    unit_id = fields.Many2one('proposal.service.unit')
    daily_hours = fields.Integer(related='proposal_service_id.daily_hours')
    weekly_days = fields.Integer(related='proposal_service_id.weekly_days')
    monthly_days = fields.Integer(related='proposal_service_id.monthly_days')
    quantity = fields.Integer(default=1)
    total_cost = fields.Float(
        related='proposal_service_id.total_cost',
        store=True,
        string='Subtotal (live)',
    )
    total = fields.Float(compute='compute_total', store=True)

    # --- Snapshot / freeze (Phase 2) -------------------------------------
    # The frozen breakdown is the source of truth once frozen; catalog edits
    # never change it. Until frozen, the line falls back to the live cost.
    frozen = fields.Boolean(string='Cost frozen', copy=False)
    snapshot_date = fields.Datetime(string='Frozen on', readonly=True, copy=False)
    cost_book_id = fields.Many2one(
        'proposal.service.cost', string='Cost Book used', readonly=True, copy=False)
    snapshot_line_ids = fields.One2many(
        'proposal.service.line.cost', 'line_id', string='Frozen breakdown', copy=True)
    frozen_unit_cost = fields.Float(string='Frozen unit cost', copy=True)
    effective_unit_cost = fields.Float(
        string='Unit cost', compute='_compute_effective', store=True,
        help="Frozen cost if the line is frozen, else the live catalog cost.")
    effective_total = fields.Float(
        string='Line total', compute='_compute_effective', store=True)

    @api.depends('quantity', 'total_cost')
    def compute_total(self):
        for rec in self:
            rec.total = rec.quantity * rec.total_cost

    @api.depends('frozen', 'frozen_unit_cost', 'total_cost', 'quantity')
    def _compute_effective(self):
        for rec in self:
            rec.effective_unit_cost = rec.frozen_unit_cost if rec.frozen else rec.total_cost
            rec.effective_total = rec.quantity * rec.effective_unit_cost

    def _freeze_from_book(self):
        """Snapshot each line's cost from the applicable customer Cost Book
        (or, if none exists, from the legacy service items). Idempotent:
        re-running replaces the snapshot — this is the explicit Re-sync."""
        Comp = self.env['proposal.cost.component']
        for rec in self:
            partner = rec.proposal_id.partner_id
            date = rec.proposal_id.proposal_date or fields.Date.context_today(rec)
            book = rec.proposal_service_id.get_cost_book(partner=partner, date=date)
            rec.snapshot_line_ids.unlink()
            if book:
                vals = [(0, 0, {
                    'component_id': l.component_id.id,
                    'name': l.component_id.name,
                    'amount': l.amount, 'note': l.note,
                }) for l in book.line_ids]
                rec.write({
                    'snapshot_line_ids': vals, 'cost_book_id': book.id,
                    'frozen': True, 'frozen_unit_cost': book.total_cost,
                    'snapshot_date': fields.Datetime.now(),
                })
            else:
                # Fallback: freeze from the legacy service.item cost lines.
                vals = []
                for item in rec.proposal_service_id.line_ids:
                    comp = Comp.search([('code', '=', item.type)], limit=1)
                    vals.append((0, 0, {
                        'component_id': comp.id if comp else False,
                        'name': comp.name if comp else (item.type or ''),
                        'amount': item.cost,
                    }))
                rec.write({
                    'snapshot_line_ids': vals, 'cost_book_id': False,
                    'frozen': True,
                    'frozen_unit_cost': rec.proposal_service_id.total_cost,
                    'snapshot_date': fields.Datetime.now(),
                })
        return True

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        # Auto-freeze new lines when the proposal already has a customer, so
        # the cost is captured at add-time.
        for line in lines:
            if not line.frozen and line.proposal_id.partner_id:
                line._freeze_from_book()
        return lines

    def get_service_cost(self, type):
        cost = 0
        lines = self.proposal_id.pricing_ids.filtered(lambda p: p.service_id.id == self.id)
        if lines:
            if type == 'material':
                cost = lines[0].material_cost
            elif type == 'equipment':
                cost = lines[0].equipment_cost
            elif type == 'transportation':
                cost = lines[0].transportation_cost
            elif type == 'cost':
                cost = lines[0].cost
            elif type == 'sales':
                cost = lines[0].sales_price
            else:
                cost = lines[0].profit_percentage
        return cost

    def get_commission_amount(self):
        pricing_line = self.proposal_id.pricing_ids.filtered(lambda p: p.service_id.id == self.id)
        return pricing_line.commission_amount if pricing_line else 0
