from odoo import _, api, fields, models


class ProposalServiceItem(models.Model):
    _name = 'proposal.service.item'
    _description = 'Proposal Service Detail'

    proposal_service_id = fields.Many2one('proposal.service')
    sequence = fields.Integer(default=10)
    type = fields.Selection(
        selection=[
            ('salary', 'Salary'),
            ('residency', 'Residency'),
            ('accommodation', 'Accommodation'),
            ('uniform', 'Uniform'),
            ('leave', 'Leave & Indemnity'),
            ('insurance', 'Staff Insurance'),
            ('bank_charge', 'Bank Charge'),
            ('medical', 'Medical Certificate'),
            ('gate_pass', 'Gate Pass'),
            ('other', 'Other'),
        ],
        required=True,
    )
    other_cost = fields.Char()
    cost = fields.Float(digits=(16, 3), )
    description = fields.Char()
