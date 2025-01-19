from odoo import fields, models, api, _
from .qr_generator import generateQrCode
from odoo.http import request
from datetime import datetime
from odoo.exceptions import ValidationError


class Proposal(models.Model):
    _name = 'proposal.proposal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Proposal'

    def generate_barcode(self):
        return str(int(datetime.now().timestamp()))

    def get_default_approvers(self):
        return [(0, 0, {
            'sequence': rec.sequence,
            'user_id': rec.user_id.id
        }) for rec in self.env['proposal.approver'].search([])]

    name = fields.Char(
        compute='compute_name',
        store=True,
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    ref = fields.Char(required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'),)
    partner_id = fields.Many2one('res.partner')
    proposal_date = fields.Date()
    expire_date = fields.Date()
    total_amount = fields.Float(
        compute='compute_total_amount',
        store=True,
        string='Total Amount',
    )
    service_type_id = fields.Many2one('proposal.service.type')
    country_id = fields.Many2one(
        'res.country',
        related='partner_id.country_id',
        store=True,
    )
    city = fields.Char(related='partner_id.city', store=True)
    phone = fields.Char(related='partner_id.phone', store=True)
    service_site = fields.Char(string='Site of Service')
    mobilization_date = fields.Date()
    proposal_period = fields.Integer()
    notes = fields.Text()
    state = fields.Selection(
        selection=[('draft', 'New'), ('submit', 'Submitted'), ('waiting', 'Waiting Approval'),
                   ('approve', 'Approved'), ('reject', 'Rejected'), ('cancel', 'Cancel'),
                   ('won', 'Won'), ('contracted', 'Contracted')],
        default='draft',
        tracking=True,
    )
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
    uniform_amount = fields.Float(compute='compute_service_amounts', store=True)
    accommodation_amount = fields.Float(compute='compute_service_amounts', store=True)
    residency_amount = fields.Float(compute='compute_service_amounts', store=True)
    leave_amount = fields.Float(compute='compute_service_amounts', store=True, string='L&A Amount')
    insurance_amount = fields.Float(compute='compute_service_amounts', store=True)
    fee_amount = fields.Float(compute='compute_service_amounts', store=True)
    other_amount = fields.Float(compute='compute_service_amounts', store=True)
    gate_amount = fields.Float(compute='compute_service_amounts', store=True)
    medical_amount = fields.Float(compute='compute_service_amounts', store=True)
    total_cost = fields.Float(compute='compute_total_cost', store=True)
    individual_cost = fields.Float(compute='compute_individual_cost', store=True)
    total_sales = fields.Float(compute='compute_total_sales', store=True)
    individual_sales = fields.Float(compute='compute_individual_sales', store=True)
    total_pricing_cost = fields.Float(
        compute='compute_total_pricing_cost',
        store=True,
        string='Total Pricing Cost',
    )
    margin_amount = fields.Float(compute='compute_margin', store=True, string='Net Profit')
    margin_percentage = fields.Float(compute='compute_margin', store=True, string='Net Profit %')
    lead_id = fields.Many2one('crm.lead')
    approver_id = fields.Many2one('res.users', compute='compute_approver', store=True)
    approver_users = fields.Many2many('res.users', compute='compute_approver_users', store=True)
    receiver_users = fields.Many2many(
        'res.users',
        'approved_users_proposal_rel',
        'proposal_id',
        'user_id',
    )
    receiver_users_str = fields.Char(compute='compute_receiver_users_str', store=True)
    user_confirmed = fields.Boolean(compute='compute_user_confirmed')
    barcode = fields.Char(default=generate_barcode)
    logo = fields.Binary(related='partner_id.image_1920', store=True, readonly=False)
    qr_image = fields.Binary("QR Image", compute='_generate_qr_code')
    qr_url = fields.Char("QR URL", compute='_generate_qr_code')
    active = fields.Boolean(default=True)
    mode = fields.Selection(selection=[
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('annually', 'Annually'),
    ])
    # print options
    print_cover = fields.Boolean(default=True)
    print_about = fields.Boolean(default=True)
    print_scope = fields.Boolean(default=True)
    print_quotation = fields.Boolean(default=True)
    print_list = fields.Boolean(default=True, string='Print List Material&Equipment')
    print_terms = fields.Boolean(default=True)
    print_acceptance = fields.Boolean(default=True)
    include_material = fields.Boolean(default=True)
    list_text = fields.Text(
        default=
        "Our Price dosn't include the materials or equipments or any machineries, we will provide you with list of most used items for the cleaning services with prices for each one to choose which one you will add to your contract to be able customize the price and contract.",
    )
    list_footer = fields.Text(
        default="Feel free and control your payment, what you need what you pay")
    term_text = fields.Text(
        default=
        "Our Price doesn't include materials or equipments and machiners. We provided you with list of the most used items for the cleaning services with individual unit price allowing you to choose your preferred items and customize your cost",
    )
    # commission
    commission_ids = fields.One2many('proposal.commission.line', 'proposal_id')
    apply_commission = fields.Boolean(string='Apply Profit Commission')
    commission_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed'),
    ])
    commission_rate = fields.Float()
    commission_amount = fields.Float(compute='compute_commission_amount', store=True)
    total_commission_amount = fields.Float(string='Total Commission')
    approval_ids = fields.One2many(
        'proposal.approval',
        'proposal_id',
        default=get_default_approvers,
    )
    material_service_ids = fields.Many2many(
        'proposal.service.line',
        domain="[('id', 'in', service_ids)]",
    )
    equipment_service_ids = fields.Many2many(
        'proposal.service.line',
        relation="equipment_service_rel",
        column1="equipment_id",
        column2="service_id",
        domain="[('id', 'in', service_ids)]",
    )

    @api.depends('apply_commission', 'commission_rate', 'commission_type', 'margin_amount')
    def compute_commission_amount(self):
        for rec in self:
            rec.commission_amount = 0
            if rec.apply_commission:
                if rec.commission_type == 'fixed':
                    rec.commission_amount = rec.commission_rate
                else:
                    rec.commission_amount = (rec.commission_rate * rec.margin_amount) / 100

    @api.depends('approval_ids', 'approval_ids.approved', 'state')
    def compute_approver(self):
        for rec in self:
            rec.approver_id = False
            approvers = rec.approval_ids.filtered(lambda a: not a.approved)
            if approvers:
                rec.approver_id = approvers[0].user_id.id

    @api.depends('approval_ids', 'approval_ids.user_id')
    def compute_approver_users(self):
        for rec in self:
            rec.approver_users = False
            if rec.approval_ids:
                rec.approver_users = [(6, 0, [u.id for u in rec.approval_ids.mapped('user_id')])]

    def compute_user_confirmed(self):
        for rec in self:
            rec.user_confirmed = False
            if rec.approval_ids and rec.approver_users:
                if self.env.uid in rec.approver_users.ids:
                    if rec.approval_ids.filtered(
                            lambda l: l.user_id.id == self.env.uid and l.approved):
                        rec.user_confirmed = True

    @api.constrains('commission_rate')
    def validate_commission_rate(self):
        for rec in self:
            if rec.commission_type == 'percentage':
                if rec.commission_rate > 100:
                    raise ValidationError("Percentage can't be more than 100%")

    @api.depends('service_type_id', 'ref', 'partner_id')
    def compute_name(self):
        for rec in self:
            name = 'Proposal'
            if rec.service_type_id:
                name += f' | {rec.service_type_id.name}'
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

    @api.depends('pricing_ids.transportation_cost', 'pricing_ids.service_quantity')
    def compute_transportation_amount(self):
        for rec in self:
            amount = 0
            for line in rec.pricing_ids:
                amount += line.service_quantity * line.transportation_cost
            rec.transportation_amount = amount

    @api.depends('manpower_ids.total_salary')
    def compute_salary_amount(self):
        for rec in self:
            rec.salary_amount = sum(rec.manpower_ids.mapped('total_salary') or [])

    @api.depends('service_ids', 'service_ids.proposal_service_id')
    def compute_service_amounts(self):
        for rec in self:
            rec.uniform_amount = 0
            rec.accommodation_amount = 0
            rec.residency_amount = 0
            rec.leave_amount = 0
            rec.insurance_amount = 0
            rec.fee_amount = 0
            rec.medical_amount = 0
            rec.other_amount = 0
            rec.gate_amount = 0

            total_uniform = 0
            total_accommodation = 0
            total_residency = 0
            total_leave = 0
            total_insurance = 0
            total_fee = 0
            total_medical = 0
            total_other = 0
            total_gate = 0
            for service_line in rec.service_ids:
                lines = service_line.proposal_service_id.line_ids
                total_uniform += sum(
                    lines.filtered(lambda l: l.type == 'uniform').mapped('cost') or
                    []) * service_line.quantity
                total_accommodation += sum(
                    lines.filtered(lambda l: l.type == 'accommodation').mapped('cost') or
                    []) * service_line.quantity
                total_residency += sum(
                    lines.filtered(lambda l: l.type == 'residency').mapped('cost') or
                    []) * service_line.quantity
                total_leave += sum(
                    lines.filtered(lambda l: l.type == 'leave').mapped('cost') or
                    []) * service_line.quantity
                total_insurance += sum(
                    lines.filtered(lambda l: l.type == 'insurance').mapped('cost') or
                    []) * service_line.quantity
                total_fee += sum(
                    lines.filtered(lambda l: l.type == 'bank_charge').mapped('cost') or
                    []) * service_line.quantity
                total_medical += sum(
                    lines.filtered(lambda l: l.type == 'medical').mapped('cost') or
                    []) * service_line.quantity
                total_other += sum(
                    lines.filtered(lambda l: l.type == 'other').mapped('cost') or
                    []) * service_line.quantity
                total_gate += sum(
                    lines.filtered(lambda l: l.type == 'gate_pass').mapped('cost') or
                    []) * service_line.quantity

            rec.uniform_amount = total_uniform
            rec.accommodation_amount = total_accommodation
            rec.residency_amount = total_residency
            rec.leave_amount = total_leave
            rec.insurance_amount = total_insurance
            rec.fee_amount = total_fee
            rec.medical_amount = total_medical
            rec.other_amount = total_other
            rec.gate_amount = total_gate

    @api.depends('material_amount', 'equipment_amount', 'transportation_amount', 'salary_amount')
    def compute_total_cost(self):
        for rec in self:
            rec.total_cost = rec.material_amount + rec.equipment_amount + rec.transportation_amount + rec.salary_amount

    @api.depends('total_cost', 'manpower_quantity')
    def compute_individual_cost(self):
        for rec in self:
            rec.individual_cost = 0
            if rec.manpower_quantity:
                rec.individual_cost = rec.total_cost / rec.manpower_quantity

    @api.depends('total_sales', 'manpower_quantity')
    def compute_individual_sales(self):
        for rec in self:
            rec.individual_sales = 0
            if rec.manpower_quantity:
                rec.individual_sales = rec.total_sales / rec.manpower_quantity

    @api.depends('pricing_ids', 'pricing_ids.sales_price')
    def compute_total_sales(self):
        for rec in self:
            rec.total_sales = sum(rec.pricing_ids.mapped('sales_price') or [])

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
            if rec.expire_date and rec.proposal_date:
                if rec.expire_date < rec.proposal_date:
                    raise ValidationError(_('Expire date cannot be earlier than proposal date!'))

    def generate_pricing(self):
        self.pricing_ids = [(5, 0, 0)]
        vals = []
        total_material_service_qty = sum(self.material_service_ids.mapped('quantity'))
        total_equipment_service_qty = sum(self.equipment_service_ids.mapped('quantity'))
        total_commission = 0
        for service_line in self.service_ids:
            material_cost = 0
            equipment_cost = 0
            transportation_cost = 0
            commission_amount = 0
            if service_line.id in self.material_service_ids.ids and total_material_service_qty:
                material_cost = self.material_amount / total_material_service_qty
            if service_line.id in self.equipment_service_ids.ids and total_equipment_service_qty and self.proposal_period:
                equipment_cost = self.equipment_amount / total_equipment_service_qty / self.proposal_period
            # transportation
            tl = self.transportation_ids.filtered(lambda t: service_line.id in t.service_ids.ids)
            if tl:
                tl = tl[0]
                if tl.type == 'group':
                    total_transportation_service_qty = sum(tl.service_ids.mapped('quantity'))
                    if total_transportation_service_qty and tl.type == 'group':
                        transportation_cost = tl.cost / total_transportation_service_qty
                else:
                    transportation_cost = tl.cost
            individual_cost = service_line.total_cost + material_cost + equipment_cost + transportation_cost
            # commission
            cl = self.commission_ids.filtered(lambda c: service_line.id in c.service_ids.ids)
            if cl:
                cl = cl[0]
                commission_amount = self.get_commission_amount(cl.commission, cl.commission_type,
                                                               cl.commission_rate, individual_cost)
                total_commission += commission_amount * service_line.quantity

            vals.append((0, 0, {
                'name': 'service',
                'service_id': service_line.id,
                'service_quantity': service_line.quantity,
                'service_individual_cost': service_line.total_cost,
                'service_total_cost': service_line.total,
                'material_cost': material_cost,
                'equipment_cost': equipment_cost,
                'transportation_cost': transportation_cost,
                'individual_cost': individual_cost,
                'commission_amount': commission_amount,
                'individual_sales_price': individual_cost,
                'cost': (individual_cost + commission_amount) * service_line.quantity,
            }))
        self.write({'pricing_ids': vals, 'total_commission_amount': total_commission})

    def get_commission_amount(self, commission, commission_type, commission_rate, individual_cost):
        commission_amount = 0
        if commission and commission_type and commission_rate:
            if commission_type == 'percentage':
                commission_amount = individual_cost * (commission_rate / 100)
            else:
                commission_amount = commission_rate
        return commission_amount

    @api.model
    def create(self, vals):
        if vals.get('ref', _('New')) == _('New'):
            vals['ref'] = self.env['ir.sequence'].next_by_code('proposal.proposal') or _('New')
        result = super(Proposal, self).create(vals)
        return result

    def button_submit(self):
        self.state = 'submit'

    def button_approve(self):
        self.approval_ids.filtered(lambda l: l.user_id.id == self.env.uid).write({
            'approved': True,
            'date_approved': fields.Datetime.now(),
        })
        if self.approval_ids.filtered(lambda l: not l.approved):
            self.write({'state': 'waiting'})
            return
        self.write({
            'state':
                'approve',
            'receiver_users':
                self.env['proposal.receiver'].sudo().search([]).mapped('user_id').mapped('id'),
        })

    @api.depends('receiver_users')
    def compute_receiver_users_str(self):
        for rec in self:
            rec.receiver_users_str = ''
            if rec.receiver_users:
                rec.receiver_users_str = ','.join(rec.receiver_users.mapped('email'))

    def button_reject(self):
        self.state = 'reject'

    def button_cancel(self):
        self.state = 'cancel'

    def button_draft(self):
        self.state = 'draft'
        self.approval_ids = [(5, 0, 0)]
        self.write({'approval_ids': self.get_default_approvers()})

    def button_won(self):
        template = self.env.ref('care_proposal.email_template_proposal_won')
        email_values = {}
        if self.approval_ids:
            last_approver = self.approval_ids.sorted('date_approved', reverse=True)[0]
            email_values = {'email_from': last_approver.user_id.email}
        name_to = ','.join(self.receiver_users.mapped('name'))
        self.env['mail.template'].with_context({
            'name_to': name_to,
            'won_email': True,
        }).browse(template.id).send_mail(
            self.id,
            email_values=email_values,
            force_send=True,
            email_layout_xmlid='mail.mail_notification_light',
        )
        self.state = 'won'

    def action_send_email(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data._xmlid_lookup('care_proposal.email_template_proposal')[2]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data._xmlid_lookup(
                'mail.email_compose_message_wizard_form')[2]
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

    def _generate_qr_code(self):
        for rec in self:
            qr_info = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            action_id = self.env.ref('care_proposal.proposal_action').id
            menu_id = self.env.ref('care_proposal.proposal_menu').id
            qr_info += '/web#id=%s&action=%s&model=%s&view_type=form&cids=&menu_id=%s' % (
                rec.id, action_id, 'proposal.proposal', menu_id)
            rec.qr_url = qr_info
            rec.qr_image = generateQrCode.generate_qr_code(qr_info)

    def get_staff(self):
        return int(
            sum(
                self.pricing_ids.filtered(lambda p: p.service_id.proposal_service_id.type ==
                                          'manpower').mapped('service_quantity')))

    def get_days_text(self):
        service_days = set([
            str(day) for day in self.service_ids.filtered(
                lambda s: s.proposal_service_id.type == 'manpower').mapped('weekly_days')
        ])
        return ','.join(service_days)

    def get_hours_text(self):
        service_hours = set([
            str(hour) for hour in self.service_ids.filtered(
                lambda s: s.proposal_service_id.type == 'manpower').mapped('daily_hours')
        ])
        return ','.join(service_hours)

