from odoo import fields, models, api, _


class Lead(models.Model):
    _inherit = 'crm.lead'

    proposal_ids = fields.One2many('proposal.proposal', 'lead_id')
    proposal_count = fields.Integer(compute='compute_proposal_count', store=True)

    @api.depends('proposal_ids')
    def compute_proposal_count(self):
        for rec in self:
            rec.proposal_count = len(rec.proposal_ids or [])

    def create_proposal(self):
        self.env['proposal.proposal'].create({
            "name": self.name,
            "partner_id": self.partner_id.id,
            "lead_id": self.id
        })
        return {
            'name': _('Proposals'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'proposal.proposal',
            'domain': [('id', 'in', self.proposal_ids.ids)],
            'target': 'current',
        }

    def action_view_proposal(self):
        return {
            'name': _('Proposals'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'proposal.proposal',
            'domain': [('id', 'in', self.proposal_ids.ids)],
            'target': 'current',
        }
