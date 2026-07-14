from odoo import api, fields, models


class ProposalCostComponent(models.Model):
    """Configurable cost-component type (Salary, Residency, Uniform, …).

    Replaces the hard-coded 10-value Selection that used to live in
    proposal.service.item and be duplicated across the codebase. New component
    types can now be added from configuration without touching code."""

    _name = 'proposal.cost.component'
    _description = 'Proposal Cost Component Type'
    _inherit = ['mail.thread']
    _order = 'sequence, id'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(
        required=True, tracking=True,
        help="Technical key, e.g. salary, residency, uniform. Keep stable.")
    sequence = fields.Integer(default=10, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, tracking=True)

    _sql_constraints = [
        ('uniq_code_company', 'unique(code, company_id)',
         'The component code must be unique per company.'),
    ]
