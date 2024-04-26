from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class Proposal(models.Model):
    _name = 'proposal.proposal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Proposal'

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    ref = fields.Char()
    partner_id = fields.Many2one('res.partner')
    proposal_date = fields.Date()
    expire_date = fields.Date()
    total_amount = fields.Float()
    margin_amount = fields.Float()
    margin_percentage = fields.Float()
    service_type = fields.Selection(selection=[
        ('cleaning_services', 'Cleaning Services'),
        ('security_services', 'Security Services'),
        ('housekeeping_services', 'Housekeeping Services'),
    ])
    country_id = fields.Many2one('res.country', related='partner_id.country_id', store=True)
    city = fields.Char(related='partner_id.city', store=True)
    phone = fields.Char(related='partner_id.phone', store=True)
    service_site = fields.Char(string='Site of Service')
    mobilization_date = fields.Date()
    proposal_period = fields.Integer()
    notes = fields.Text()
    state = fields.Selection(selection=[
        ('draft', 'New'), ('progress', 'In Progress'), ('done', 'Done'),
    ], default='draft')
    service_ids = fields.One2many('proposal.service.line', 'proposal_id')
    scope_ids = fields.One2many('proposal.scope.line', 'proposal_id')
    manpower_ids = fields.One2many('proposal.manpower.line', 'proposal_id')
    material_ids = fields.One2many('proposal.material.line', 'proposal_id')
    equipment_ids = fields.One2many('proposal.equipment.line', 'proposal_id')
    transportation_ids = fields.One2many('proposal.transportation.line', 'proposal_id')
    term_ids = fields.One2many('proposal.term.line', 'proposal_id')
    pricing_ids = fields.One2many('proposal.pricing.line', 'proposal_id')
    service_quantity = fields.Integer(compute='compute_service_quantity', store=True)
    manpower_quantity = fields.Integer(compute='compute_manpower_quantity', store=True)
    material_amount = fields.Float(compute='compute_material_amount', store=True)
    equipment_amount = fields.Float(compute='compute_equipment_amount', store=True)
    transportation_amount = fields.Float(compute='compute_transportation_amount', store=True)
    salary_amount = fields.Float(compute='compute_salary_amount', store=True)
    total_cost = fields.Float(compute='compute_total_cost', store=True)

    @api.depends('service_ids')
    def compute_service_quantity(self):
        for rec in self:
            rec.service_quantity = len(rec.service_ids or [])

    @api.depends('manpower_ids.quantity')
    def compute_manpower_quantity(self):
        for rec in self:
            rec.manpower_quantity = sum(rec.manpower_ids.mapped('quantity') or [])

    @api.depends('material_ids.cost')
    def compute_material_amount(self):
        for rec in self:
            rec.material_amount = sum(rec.material_ids.mapped('cost') or [])

    @api.depends('equipment_ids.cost')
    def compute_equipment_amount(self):
        for rec in self:
            rec.equipment_amount = sum(rec.equipment_ids.mapped('cost') or [])

    @api.depends('transportation_ids.cost')
    def compute_transportation_amount(self):
        for rec in self:
            rec.transportation_amount = sum(rec.transportation_ids.mapped('cost') or [])

    @api.depends('manpower_ids.total_salary')
    def compute_salary_amount(self):
        for rec in self:
            rec.salary_amount = sum(rec.manpower_ids.mapped('total_salary') or [])

    @api.depends('material_amount', 'equipment_amount', 'transportation_amount', 'salary_amount')
    def compute_total_cost(self):
        for rec in self:
            rec.total_cost = rec.material_amount + rec.equipment_amount + rec.transportation_amount + rec.salary_amount

    @api.constrains('proposal_date', 'expire_date')
    def check_dates(self):
        for rec in self:
            if rec.proposal_date < rec.expire_date:
                raise ValidationError(_('Expire date cannot be earlier than proposal date!'))

    def generate_pricing(self):
        self.pricing_ids = [(5, 0, 0)]
        vals = []
        for line in self.service_ids:
            vals.append((0, 0, {
                'name': line.proposal_service_id.name,
                'cost': line.total_cost
            }))
        for line in self.material_ids:
            vals.append((0, 0, {
                'name': line.product_id.name,
                'cost': line.cost
            }))
        for line in self.equipment_ids:
            vals.append((0, 0, {
                'name': line.product_id.name,
                'cost': line.cost
            }))
        for line in self.transportation_ids:
            vals.append((0, 0, {
                'name': line.transportation_id.name,
                'cost': line.cost
            }))
        self.write({
            'pricing_ids': vals
        })


class ProposalServiceLine(models.Model):
    _name = 'proposal.service.line'
    _rec_name = 'proposal_service_id'
    _description = 'Proposal Service Line'

    proposal_id = fields.Many2one('proposal.proposal')
    proposal_service_id = fields.Many2one('proposal.service', required=True, string='Service')
    daily_hours = fields.Integer(related='proposal_service_id.daily_hours')
    weekly_days = fields.Integer(related='proposal_service_id.weekly_days')
    monthly_days = fields.Integer(related='proposal_service_id.monthly_days')
    total_cost = fields.Float(related='proposal_service_id.total_cost', store=True)


class ProposalScopeLine(models.Model):
    _name = 'proposal.scope.line'
    _description = 'Proposal Scope Line'

    proposal_id = fields.Many2one('proposal.proposal')
    proposal_scope_id = fields.Many2one('proposal.scope', required=True, string='Scope')
    schedule = fields.Selection(selection=[
        ('daily', 'Daily'), ('weekly', 'Weekly'),
        ('monthly', 'Monthly'), ('custom', 'As Per Request'), ('other', 'Other'),
    ], related='proposal_scope_id.schedule')


class ProposalManpowerLine(models.Model):
    _name = 'proposal.manpower.line'
    _description = 'Proposal Manpower Line'

    proposal_id = fields.Many2one('proposal.proposal')
    proposal_manpower_id = fields.Many2one('proposal.manpower', required=True, string='Manpower')
    nationality = fields.Many2one('res.country', related='proposal_manpower_id.nationality')
    gender = fields.Selection(selection=[
        ('male', 'Male'), ('female', 'Female'),
    ], related='proposal_manpower_id.gender')
    quantity = fields.Integer(default=1)
    service_ids = fields.Many2many('proposal.service.line', compute='compute_service_ids', store=True)
    service_id = fields.Many2one('proposal.service.line', domain="[('id', 'in', service_ids)]")
    salary = fields.Float(compute='compute_salary', store=True)
    total_salary = fields.Float(compute='compute_total_salary', store=True)

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
                rec.salary = sum(rec.service_id.proposal_service_id.line_ids.filtered(lambda l: l.type == 'salary').mapped('cost'))

    @api.depends('quantity', 'salary')
    def compute_total_salary(self):
        for rec in self:
            rec.total_salary = rec.quantity * rec.salary


class ProposalMaterialLine(models.Model):
    _name = 'proposal.material.line'
    _description = 'Proposal Material Line'

    proposal_id = fields.Many2one('proposal.proposal')
    product_id = fields.Many2one('product.product', required=True, string='Material')
    cost = fields.Float(required=True)

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.cost = self.product_id.standard_price


class ProposalEquipmentLine(models.Model):
    _name = 'proposal.equipment.line'
    _description = 'Proposal Equipment Line'

    proposal_id = fields.Many2one('proposal.proposal')
    product_id = fields.Many2one('product.product', required=True, string='Equipment')
    cost = fields.Float(required=True)

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.cost = self.product_id.standard_price


class ProposalTransportationLine(models.Model):
    _name = 'proposal.transportation.line'
    _description = 'Proposal Transportation Line'

    proposal_id = fields.Many2one('proposal.proposal')
    transportation_id = fields.Many2one('proposal.transportation', required=True)
    cost = fields.Float(related='transportation_id.cost', store=True)
    period = fields.Selection(selection=[
        ('monthly', 'Monthly'), ('daily', 'Daily'),
    ], related='transportation_id.period')


class ProposalTermLine(models.Model):
    _name = 'proposal.term.line'
    _description = 'Proposal Term Line'

    proposal_id = fields.Many2one('proposal.proposal')
    term_id = fields.Many2one('proposal.term', required=True)


class ProposalPricingLine(models.Model):
    _name = 'proposal.pricing.line'
    _description = 'Proposal Pricing Line'

    proposal_id = fields.Many2one('proposal.proposal')
    name = fields.Char(required=True)
    cost = fields.Float(required=True)
