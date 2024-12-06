from odoo import _, api, fields, models


class ProposalManpowerLine(models.Model):
    _name = 'proposal.manpower.line'
    _description = 'Proposal Manpower Line'

    proposal_id = fields.Many2one('proposal.proposal')
    proposal_manpower_id = fields.Many2one(
        'proposal.manpower',
        required=True,
        string='Manpower',
    )
    nationality = fields.Many2one('res.country', related='proposal_manpower_id.nationality')
    gender = fields.Selection(
        related='proposal_manpower_id.gender',
    )
    quantity = fields.Integer(default=1)
    service_ids = fields.Many2many(
        'proposal.service.line',
        compute='compute_service_ids',
        store=True,
        string='Services',
    )
    service_id = fields.Many2one(
        'proposal.service.line',
        domain="[('id', 'in', service_ids)]",
        string='Service',
    )
    salary = fields.Float(
        compute='compute_salary',
        store=True,
    )
    total_salary = fields.Float(
        compute='compute_total_salary',
        store=True,
    )

    @api.depends('proposal_id.service_ids')
    def compute_service_ids(self):
        for rec in self:
            rec.service_ids = False
            if rec.proposal_id.service_ids:
                rec.service_ids = [(6, 0, rec.proposal_id.service_ids.ids)]

    @api.depends('service_id.proposal_service_id')
    def compute_salary(self):
        for rec in self:
            rec.salary = 0
            if rec.service_id.proposal_service_id:
                rec.salary = sum(
                    rec.service_id.proposal_service_id.line_ids.filtered(
                        lambda l: l.type == 'salary').mapped('cost'))

    @api.depends('quantity', 'salary')
    def compute_total_salary(self):
        for rec in self:
            rec.total_salary = rec.quantity * rec.salary
