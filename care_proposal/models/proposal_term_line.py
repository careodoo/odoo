from odoo import _, api, fields, models

class ProposalTermLine(models.Model):
    _name = 'proposal.term.line'
    _description = 'Proposal Term Line'

    proposal_id = fields.Many2one('proposal.proposal')
    term_id = fields.Many2one('proposal.term', required=True)