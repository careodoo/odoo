from odoo import fields, models, api, _


class Lead(models.Model):
    _inherit = 'crm.lead'

    proposal_ids = fields.One2many('proposal.proposal', 'lead_id')
    proposal_count = fields.Integer(compute='compute_proposal_count', store=True)
    winning_proposal_id = fields.Many2one(
        'proposal.proposal', string='Winning Proposal', copy=False,
        domain="[('id','in',proposal_ids)]",
        help="The proposal selected as the winning quotation for this opportunity.")
    proposal_best_amount = fields.Monetary(
        string='Best Proposal', compute='_compute_proposal_amounts',
        currency_field='company_currency')

    @api.depends('proposal_ids')
    def compute_proposal_count(self):
        for rec in self:
            rec.proposal_count = len(rec.proposal_ids or [])

    @api.depends('proposal_ids.total_amount', 'proposal_ids.state', 'winning_proposal_id')
    def _compute_proposal_amounts(self):
        for rec in self:
            if rec.winning_proposal_id:
                rec.proposal_best_amount = rec.winning_proposal_id.total_amount
            else:
                live = rec.proposal_ids.filtered(
                    lambda p: p.state not in ('cancel', 'reject') and not p.superseded)
                rec.proposal_best_amount = max(live.mapped('total_amount') or [0.0])

    def create_proposal(self):
        proposal = self.env['proposal.proposal'].create({
            "name": self.name,
            "partner_id": self.partner_id.id,
            "lead_id": self.id,
            "proposal_date": fields.Date.context_today(self),
        })
        # Open the freshly-created proposal directly so the user can fill it in.
        return {
            'name': _('Proposal'),
            'type': 'ir.actions.act_window',
            'res_model': 'proposal.proposal',
            'res_id': proposal.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_proposal(self):
        return {
            'name': _('Proposals'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'proposal.proposal',
            'domain': [('id', 'in', self.proposal_ids.ids)],
            'target': 'current',
        }

    def _sync_won_proposal(self, proposal):
        """A proposal was won: record it as the winning quotation, roll the
        amount up to expected_revenue, supersede the competing proposals and
        move the opportunity to Won."""
        self.ensure_one()
        self.winning_proposal_id = proposal.id
        self.expected_revenue = proposal.total_amount
        others = self.proposal_ids - proposal
        others.filtered(lambda p: p.state not in ('won', 'cancel', 'reject')).write({'superseded': True})
        if self.type == 'opportunity' and not self.stage_id.is_won:
            try:
                self.action_set_won()
            except Exception:
                # Don't let CRM-stage quirks block the proposal workflow.
                pass

    def action_set_lost(self, **additional_values):
        res = super().action_set_lost(**additional_values)
        for lead in self:
            lead.proposal_ids.filtered(
                lambda p: p.state not in ('won', 'cancel', 'reject')).button_cancel()
        return res
