from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class Proposal(models.Model):
    _name = 'proposal.proposal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Proposal'

    def _default_approver(self):
        IPC = self.env['ir.config_parameter'].sudo()
        approver = False
        approver_str = IPC.get_param('care_proposal.proposal_approver_id')
        if approver_str:
            approver = self.env['res.users'].browse(int(approver_str))
        return approver.id if approver else False

    name = fields.Char(compute='compute_name', store=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    ref = fields.Char(required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner')
    proposal_date = fields.Date()
    expire_date = fields.Date()
    total_amount = fields.Float(compute='compute_total_amount', store=True)
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
        ('draft', 'New'), ('submit', 'Submitted'),
        ('approve', 'Approved'), ('reject', 'Rejected')
    ], default='draft', tracking=True)
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
    total_pricing_cost = fields.Float(compute='compute_total_pricing_cost', store=True)
    margin_amount = fields.Float(compute='compute_margin', store=True)
    margin_percentage = fields.Float(compute='compute_margin', store=True, string='Margin %')
    lead_ids = fields.One2many('crm.lead', 'proposal_id')
    approver_id = fields.Many2one('res.users', default=_default_approver)

    @api.depends('service_type', 'ref', 'partner_id')
    def compute_name(self):
        for rec in self:
            name = 'Proposal'
            if rec.service_type == 'cleaning_services':
                name += ' | Cleaning Services'
            elif rec.service_type == 'security_services':
                name += ' | Security Services'
            elif rec.service_type == 'housekeeping_services':
                name += ' | Housekeeping Services'
            if rec.partner_id:
                name += ' | ' + rec.partner_id.name
            if rec.ref:
                name += ' | ' + rec.ref
            rec.name = name

    @api.depends('service_ids')
    def compute_service_quantity(self):
        for rec in self:
            rec.service_quantity = len(rec.service_ids or [])

    @api.depends('manpower_ids.quantity')
    def compute_manpower_quantity(self):
        for rec in self:
            rec.manpower_quantity = sum(rec.manpower_ids.mapped('quantity') or [])

    @api.depends('material_ids.total_amount')
    def compute_material_amount(self):
        for rec in self:
            rec.material_amount = sum(rec.material_ids.mapped('total_amount') or [])

    @api.depends('equipment_ids.total_amount')
    def compute_equipment_amount(self):
        for rec in self:
            rec.equipment_amount = sum(rec.equipment_ids.mapped('total_amount') or [])

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

    @api.depends('pricing_ids.sales_price')
    def compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.pricing_ids.mapped('sales_price') or [])

    @api.depends('pricing_ids.cost')
    def compute_total_pricing_cost(self):
        for rec in self:
            rec.total_pricing_cost = sum(rec.pricing_ids.mapped('cost') or [])

    @api.depends('total_amount', 'total_pricing_cost')
    def compute_margin(self):
        for rec in self:
            rec.margin_amount = rec.total_amount - rec.total_pricing_cost
            rec.margin_percentage = 0
            if rec.margin_amount and rec.total_amount:
                rec.margin_percentage = (rec.margin_amount / rec.total_amount) * 100

    @api.constrains('proposal_date', 'expire_date')
    def check_dates(self):
        for rec in self:
            if rec.expire_date < rec.proposal_date:
                raise ValidationError(_('Expire date cannot be earlier than proposal date!'))

    def generate_pricing(self):
        self.pricing_ids = [(5, 0, 0)]
        vals = []
        total = sum([line.total_cost for line in self.service_ids])
        if total:
            vals.append((0, 0, {
                'name': 'service',
                'cost': total
            }))
        total = sum([line.total_amount for line in self.material_ids])
        if total:
            vals.append((0, 0, {
                'name': 'material',
                'cost': total
            }))
        total = sum([line.total_amount for line in self.equipment_ids])
        if total:
            vals.append((0, 0, {
                'name': 'equipment',
                'cost': total
            }))
        total = sum([line.cost for line in self.transportation_ids])
        if total:
            vals.append((0, 0, {
                'name': 'transportation',
                'cost': total
            }))
        self.write({
            'pricing_ids': vals
        })

    @api.model
    def create(self, vals):
        if vals.get('ref', _('New')) == _('New'):
            vals['ref'] = self.env['ir.sequence'].next_by_code('proposal.proposal') or _('New')
        result = super(Proposal, self).create(vals)
        return result

    def button_submit(self):
        self.state = 'submit'
        self.sudo().activity_schedule(
            'care_proposal.mail_act_proposal_submit',
            summary='Proposal',
            note='Ask To Confirm Proposal',
            user_id=self.approver_id.id)

    def button_approve(self):
        self.state = 'approve'

    def button_reject(self):
        self.state = 'reject'

    def action_send_email(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data._xmlid_lookup('care_proposal.email_template_proposal')[2]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data._xmlid_lookup('mail.email_compose_message_wizard_form')[2]
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'proposal.proposal',
            'active_model': 'proposal.proposal',
            'model_description': 'Proposal',
            'active_id': self.ids[0],
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'custom_layout': "mail.mail_notification_paynow",
            'force_email': True,
            'mark_rfq_as_sent': True,
        })

        lang = self.env.context.get('lang')
        if {'default_template_id', 'default_model', 'default_res_id'} <= ctx.keys():
            template = self.env['mail.template'].browse(ctx['default_template_id'])
            if template and template.lang:
                lang = template._render_lang([ctx['default_res_id']])[ctx['default_res_id']]

        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }


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
    quantity = fields.Float(default=1)
    cost = fields.Float(required=True)
    total_amount = fields.Float(compute='compute_total_amount', store=True, string='Total')

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.cost = self.product_id.standard_price

    @api.depends('cost', 'quantity')
    def compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.cost * rec.quantity


class ProposalEquipmentLine(models.Model):
    _name = 'proposal.equipment.line'
    _description = 'Proposal Equipment Line'

    proposal_id = fields.Many2one('proposal.proposal')
    product_id = fields.Many2one('product.product', required=True, string='Equipment')
    quantity = fields.Float(default=1)
    cost = fields.Float(required=True)
    total_amount = fields.Float(compute='compute_total_amount', store=True, string='Total')

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.cost = self.product_id.standard_price

    @api.depends('cost', 'quantity')
    def compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.cost * rec.quantity


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
    name = fields.Selection(selection=[
        ('service', 'Services'), ('material', 'Materials'),
        ('equipment', 'Equipments'), ('transportation', 'Transportations'),
    ], required=True)
    profit_percentage = fields.Float(string='Profit %')
    cost = fields.Float(required=True)
    sales_price = fields.Float(compute='compute_sales_price', store=True)

    @api.depends('profit_percentage', 'cost')
    def compute_sales_price(self):
        for rec in self:
            rec.sales_price = rec.cost + (rec.cost * (rec.profit_percentage / 100))
