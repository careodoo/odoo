from odoo import fields, models, api, _


class Lead(models.Model):
    _inherit = 'crm.lead'

    proposal_id = fields.Many2one('proposal.proposal')

    def create_proposal(self):
        proposal_id = self.env['proposal.proposal'].create({
            "name": self.name,
            "partner_id": self.partner_id.id,
        })
        self.proposal_id = proposal_id.id
        return {
            'name': _('Proposal'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'proposal.proposal',
            'res_id': proposal_id.id,
            'target': 'current',
        }

    def action_view_proposal(self):
        return {
            'name': _('Proposal'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'proposal.proposal',
            'res_id': self.proposal_id.id,
            'target': 'current',
        }
