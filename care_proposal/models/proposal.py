from odoo import fields, models, api, _
from .qr_generator import generateQrCode
from odoo.http import request
from datetime import datetime
from odoo.exceptions import ValidationError, UserError


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
    total_amount = fields.Float(digits=(16, 3), 
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
    service_ids = fields.One2many('proposal.service.line', 'proposal_id', copy=True)
    scope_ids = fields.One2many('proposal.scope.line', 'proposal_id', copy=True)
    manpower_ids = fields.One2many('proposal.manpower.line', 'proposal_id', copy=True)
    material_ids = fields.One2many('proposal.material.line', 'proposal_id', copy=True)
    equipment_ids = fields.One2many('proposal.equipment.line', 'proposal_id', copy=True)
    transportation_ids = fields.One2many('proposal.transportation.line', 'proposal_id', copy=True)
    term_ids = fields.One2many('proposal.term.line', 'proposal_id', copy=True)
    # pricing is regenerated on the copy, not duplicated
    pricing_ids = fields.One2many('proposal.pricing.line', 'proposal_id')
    service_quantity = fields.Integer(compute='compute_service_quantity', store=True)
    manpower_quantity = fields.Integer(compute='compute_manpower_quantity', store=True)
    material_amount = fields.Float(digits=(16, 3), compute='compute_material_amount', store=True)
    equipment_amount = fields.Float(digits=(16, 3), compute='compute_equipment_amount', store=True)
    transportation_amount = fields.Float(digits=(16, 3), compute='compute_transportation_amount', store=True)
    salary_amount = fields.Float(digits=(16, 3), compute='compute_salary_amount', store=True)
    uniform_amount = fields.Float(digits=(16, 3), compute='compute_service_amounts', store=True)
    accommodation_amount = fields.Float(digits=(16, 3), compute='compute_service_amounts', store=True)
    residency_amount = fields.Float(digits=(16, 3), compute='compute_service_amounts', store=True)
    leave_amount = fields.Float(digits=(16, 3), compute='compute_service_amounts', store=True, string='L&A Amount')
    insurance_amount = fields.Float(digits=(16, 3), compute='compute_service_amounts', store=True)
    fee_amount = fields.Float(digits=(16, 3), compute='compute_service_amounts', store=True)
    other_amount = fields.Float(digits=(16, 3), compute='compute_service_amounts', store=True)
    gate_amount = fields.Float(digits=(16, 3), compute='compute_service_amounts', store=True)
    medical_amount = fields.Float(digits=(16, 3), compute='compute_service_amounts', store=True)
    total_cost = fields.Float(digits=(16, 3), compute='compute_total_cost', store=True)
    individual_cost = fields.Float(digits=(16, 3), compute='compute_individual_cost', store=True)
    total_sales = fields.Float(digits=(16, 3), compute='compute_total_sales', store=True)
    individual_sales = fields.Float(digits=(16, 3), compute='compute_individual_sales', store=True)
    total_pricing_cost = fields.Float(digits=(16, 3), 
        compute='compute_total_pricing_cost',
        store=True,
        string='Total Pricing Cost',
    )
    margin_amount = fields.Float(digits=(16, 3), compute='compute_margin', store=True, string='Net Profit')
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
    commission_ids = fields.One2many('proposal.commission.line', 'proposal_id', copy=True)
    apply_commission = fields.Boolean(string='Apply Profit Commission')
    commission_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed'),
    ])
    commission_rate = fields.Float()
    commission_amount = fields.Float(digits=(16, 3), compute='compute_commission_amount', store=True)
    total_commission_amount = fields.Float(digits=(16, 3), string='Total Commission')
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

    # The body reads quantity and every cost component, so it must depend on
    # them: correcting a wage in the catalogue or a headcount on a line used
    # to leave all nine amounts frozen at their old values — and those are
    # what the cost sheet prints.
    @api.depends('service_ids', 'service_ids.proposal_service_id',
                 'service_ids.quantity',
                 'service_ids.proposal_service_id.line_ids.cost',
                 'service_ids.proposal_service_id.line_ids.type')
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

    # Every component below is computed into its own field a few lines up, but
    # only four of them were being summed — residency, uniform, leave and
    # indemnity, insurance, medical, gate pass, fees and accommodation were all
    # left out. On a live quotation that hid KD 133.000 of real cost, and the
    # header then showed a "cost" that no other number in the module agreed
    # with.
    COST_COMPONENTS = (
        'material_amount', 'equipment_amount', 'transportation_amount',
        'salary_amount', 'residency_amount', 'uniform_amount', 'leave_amount',
        'insurance_amount', 'medical_amount', 'gate_amount', 'fee_amount',
        'other_amount', 'accommodation_amount', 'commission_amount',
    )

    @api.depends(*COST_COMPONENTS)
    def compute_total_cost(self):
        for rec in self:
            rec.total_cost = sum((rec[f] or 0.0) for f in rec.COST_COMPONENTS)

    cost_reconciliation_gap = fields.Float(
        digits=(16, 3), string='Cost reconciliation gap',
        compute='_compute_cost_gap',
        help='Component total minus the cost the price was actually built on. '
             'Anything other than zero means the breakdown and the price '
             'disagree, and one of them is wrong.')

    @api.depends('total_cost', 'total_pricing_cost')
    def _compute_cost_gap(self):
        for rec in self:
            rec.cost_reconciliation_gap = (rec.total_cost or 0.0) - (rec.total_pricing_cost or 0.0)

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

    # --- Snapshot / freeze costs (Phase 2) -------------------------------
    frozen_service_count = fields.Integer(
        compute='_compute_frozen_service_count', string='Frozen services')
    service_count_total = fields.Integer(
        compute='_compute_frozen_service_count', string='Services')

    @api.depends('service_ids.frozen')
    def _compute_frozen_service_count(self):
        for rec in self:
            rec.service_count_total = len(rec.service_ids)
            rec.frozen_service_count = len(rec.service_ids.filtered('frozen'))

    def action_resync_costs(self):
        """Freeze / re-sync every service line's cost from the customer's
        active Cost Books (the only, explicit way catalog costs enter a
        proposal). Existing proposals never change unless this is pressed."""
        for rec in self:
            if not rec.partner_id:
                raise UserError(_("Select a customer before freezing costs from the cost books."))
            rec.service_ids._freeze_from_book()
            rec.message_post(body=_("Service costs frozen / re-synced from the customer cost books."))
        return True

    # --- Duplicate / Revisions / Currency (Phase 4) ----------------------
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id, tracking=True)
    revision_of_id = fields.Many2one(
        'proposal.proposal', string='Revision of', copy=False, index=True)
    version = fields.Integer(default=1, copy=False, tracking=True)
    revision_ids = fields.One2many(
        'proposal.proposal', 'revision_of_id', string='Revisions')
    revision_count = fields.Integer(compute='_compute_revision_count')
    superseded = fields.Boolean(copy=False, tracking=True)

    # Validity countdown (for the professional list view)
    days_to_expire = fields.Integer(compute='_compute_validity', store=True)
    validity_state = fields.Selection([
        ('none', '—'), ('valid', 'Valid'), ('expiring', 'Expiring soon'), ('expired', 'Expired'),
    ], compute='_compute_validity', store=True)

    @api.depends('expire_date', 'state')
    def _compute_validity(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.expire_date and rec.state in ('draft', 'submit', 'waiting', 'approve'):
                delta = (rec.expire_date - today).days
                rec.days_to_expire = delta
                rec.validity_state = 'expired' if delta < 0 else ('expiring' if delta <= 7 else 'valid')
            else:
                rec.days_to_expire = 0
                rec.validity_state = 'none'

    def _compute_revision_count(self):
        for rec in self:
            root = rec.revision_of_id or rec
            rec.revision_count = len(root.revision_ids) + (1 if rec.revision_of_id else 0)

    def copy(self, default=None):
        default = dict(default or {})
        default.setdefault('state', 'draft')
        default.setdefault('superseded', False)
        default.setdefault('approval_ids', [(5, 0, 0)])
        new = super().copy(default)
        new._remap_service_references(self)
        return new

    def _remap_service_references(self, source):
        """Point every service reference at the copy's own lines.

        service_ids is copy=True, so a duplicate gets brand-new service lines
        with new ids — but the many2many columns that say which lines carry
        material, equipment, transport or commission copy by REFERENCE and
        keep pointing at the original proposal. generate_pricing then matches
        none of them, and the revision is quoted without its material,
        equipment or transport cost at all. Silently, and below cost.
        """
        self.ensure_one()
        old_lines, new_lines = source.service_ids, self.service_ids
        if not old_lines or len(old_lines) != len(new_lines):
            return
        # copy() preserves order, so pair them positionally — the lines carry
        # no natural key to match on.
        remap = {o.id: n.id for o, n in zip(old_lines, new_lines)}

        def mapped(recs):
            return [remap[r.id] for r in recs if r.id in remap]

        vals = {}
        for fname in ('material_service_ids', 'equipment_service_ids'):
            if fname in self._fields:
                vals[fname] = [(6, 0, mapped(self[fname]))]
        if vals:
            self.write(vals)
        for fname in ('transportation_ids', 'commission_ids'):
            if fname not in self._fields:
                continue
            for line in self[fname]:
                if 'service_ids' in line._fields and line.service_ids:
                    line.service_ids = [(6, 0, mapped(line.service_ids))]

    def action_duplicate(self):
        """Exact copy of this quotation (new ref, Draft). Frozen snapshot costs
        are carried over (copy=True on the snapshot lines)."""
        self.ensure_one()
        new = self.copy()
        return self._open_proposal(new)

    def action_new_revision(self):
        """Create the next revision (vN+1) of this quotation and mark the
        current one as superseded."""
        self.ensure_one()
        root = self.revision_of_id or self
        versions = root.revision_ids.mapped('version') + [root.version]
        new = self.copy({'revision_of_id': root.id, 'version': max(versions) + 1})
        self.superseded = True
        return self._open_proposal(new)

    def action_view_revisions(self):
        self.ensure_one()
        root = self.revision_of_id or self
        return {
            'name': _('Revisions'),
            'type': 'ir.actions.act_window',
            'res_model': 'proposal.proposal',
            'view_mode': 'tree,form',
            'domain': ['|', ('id', '=', root.id), ('revision_of_id', '=', root.id)],
        }

    def _open_proposal(self, proposal):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'proposal.proposal',
            'res_id': proposal.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _email_settings(self):
        """Email customization (read from settings) + formatted values, used by
        the customer email template (mail QWeb can't call get_param directly)."""
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()

        def g(key, default):
            return ICP.get_param('care_proposal.%s' % key, default)

        def flag(key):
            return str(g(key, 'True')).lower() not in ('false', '0', '')

        return {
            'accent': g('email_accent', '#875a7b') or '#875a7b',
            'show_header': flag('email_show_header'),
            'show_summary': flag('email_show_summary'),
            'intro': g('email_intro', "It's great to send you our proposal today; we hope you will "
                       "be our valued customer."),
            'footer': g('email_footer', 'We look forward to hearing from you soon.'),
            'signature': g('email_signature', 'Care Cleaning Co. — Sales Team'),
            'total': '{:,.3f}'.format(self.total_amount or 0.0),
            'currency': self.currency_id.name or '',
            'base_url': self.get_base_url(),
        }

    def action_open_self(self):
        self.ensure_one()
        return self._open_proposal(self)

    def action_open_decision(self):
        """Open a compact decision dialog (pricing summary + workflow buttons)
        straight from the list, without navigating into the full record."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pricing Decision — %s') % (self.name or self.ref or ''),
            'res_model': 'proposal.proposal',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(self.env.ref('care_proposal.proposal_decision_form').id, 'form')],
            'target': 'new',
        }

    # --- Pricing Workspace: margin strategy / scenarios / guard (Phase 3) -
    pricing_strategy = fields.Selection([
        ('cost_plus', 'Cost-plus %'),
        ('target_margin', 'Target margin %'),
        ('target_price', 'Target price'),
        ('manual', 'Manual'),
    ], default='target_margin', tracking=True)
    target_margin_pct = fields.Float(string='Margin %', default=20.0, tracking=True)
    target_price = fields.Float(digits=(16, 3), string='Target price', tracking=True)
    price_round = fields.Float(string='Round to', default=1.0,
                               help="Round customer unit prices to this step (0 = no rounding).")
    margin_guard_pct = fields.Float(string='Margin guard %', default=10.0, tracking=True,
                                    help="Lines whose profit % is below this are flagged for review/approval.")
    below_guard = fields.Boolean(string='Below margin guard',
                                 compute='_compute_below_guard', store=True)
    # Scenarios
    scenario_economy_pct = fields.Float(string='Economy %', default=15.0)
    scenario_standard_pct = fields.Float(string='Standard %', default=22.0)
    scenario_premium_pct = fields.Float(string='Premium %', default=32.0)
    scenario_economy_price = fields.Float(digits=(16, 3), compute='_compute_scenarios')
    scenario_standard_price = fields.Float(digits=(16, 3), compute='_compute_scenarios')
    scenario_premium_price = fields.Float(digits=(16, 3), compute='_compute_scenarios')

    @api.depends('pricing_ids.below_guard')
    def _compute_below_guard(self):
        for rec in self:
            rec.below_guard = any(rec.pricing_ids.mapped('below_guard'))

    @api.depends('total_pricing_cost', 'scenario_economy_pct',
                 'scenario_standard_pct', 'scenario_premium_pct')
    def _compute_scenarios(self):
        for rec in self:
            cost = rec.total_pricing_cost or 0.0
            rec.scenario_economy_price = rec._price_for_margin(cost, rec.scenario_economy_pct)
            rec.scenario_standard_price = rec._price_for_margin(cost, rec.scenario_standard_pct)
            rec.scenario_premium_price = rec._price_for_margin(cost, rec.scenario_premium_pct)

    def _customer_price(self, cost):
        """A cost turned into something a customer may see.

        The materials and equipment tables printed product.standard_price
        under a column headed "Price", so the client could read our purchase
        cost and derive the margin on the line.
        """
        self.ensure_one()
        return self._price_for_margin(cost or 0.0, self.target_margin_pct or 0.0)

    @staticmethod
    def _price_for_margin(cost, margin_pct):
        """Selling price that yields ``margin_pct`` margin-on-price."""
        if margin_pct and margin_pct >= 100:
            # 1/(1-1) is infinite. Returning the cost unchanged turned a
            # fat-fingered 100 (meant as 10) into a deliberate-looking
            # zero-margin quote.
            raise UserError(_(
                'A margin of %s%% is not achievable — margin on price must be '
                'below 100%%.') % margin_pct)
        if margin_pct:
            return cost / (1.0 - margin_pct / 100.0)
        return cost

    def _round_price(self, value):
        rnd = self.price_round or 0.0
        if rnd and rnd > 0:
            return round(value / rnd) * rnd
        return value

    def action_apply_margin(self):
        """Set every pricing line's unit sales price from its (cost+commission)
        using the chosen strategy, then round. 'manual' leaves prices alone."""
        for rec in self:
            if not rec.pricing_ids:
                rec.generate_pricing()
            strat = rec.pricing_strategy
            if strat == 'manual':
                continue
            lines = rec.pricing_ids
            if strat == 'target_price' and rec.target_price:
                base_total = sum(l.individual_cost_after_commission * l.service_quantity for l in lines)
                if base_total:
                    factor = rec.target_price / base_total
                    for l in lines:
                        l.individual_sales_price = rec._round_price(l.individual_cost_after_commission * factor)
                continue
            m = rec.target_margin_pct or 0.0
            for l in lines:
                base = l.individual_cost_after_commission
                if strat == 'cost_plus':
                    price = base * (1.0 + m / 100.0)
                else:  # target_margin
                    price = rec._price_for_margin(base, m)
                l.individual_sales_price = rec._round_price(price)
        return True

    def _apply_scenario(self, pct):
        self.write({'pricing_strategy': 'target_margin', 'target_margin_pct': pct})
        return self.action_apply_margin()

    def action_apply_economy(self):
        return self._apply_scenario(self.scenario_economy_pct)

    def action_apply_standard(self):
        return self._apply_scenario(self.scenario_standard_pct)

    def action_apply_premium(self):
        return self._apply_scenario(self.scenario_premium_pct)

    @api.model
    def get_dashboard_data(self, year=None):
        """Aggregate KPIs + chart series for the OWL proposal dashboard."""
        domain = []
        if year and str(year) != 'all':
            domain += [('proposal_date', '>=', '%s-01-01' % year),
                       ('proposal_date', '<=', '%s-12-31' % year)]
        props = self.search(domain)
        WON = ('won', 'contracted')
        ACTIVE = ('draft', 'submit', 'waiting', 'approve')
        LOST = ('reject', 'cancel')
        won = props.filtered(lambda p: p.state in WON)
        lost = props.filtered(lambda p: p.state in LOST)
        active = props.filtered(lambda p: p.state in ACTIVE)
        decided = len(won) + len(lost)
        win_rate = round(len(won) / decided * 100, 1) if decided else 0.0
        margins = [p.margin_percentage for p in props if p.margin_percentage]
        avg_margin = round(sum(margins) / len(margins), 1) if margins else 0.0

        labels = dict(self._fields['state'].selection)
        sd = {}
        for p in props:
            sd[p.state] = sd.get(p.state, 0) + 1
        status_dist = [{'key': k, 'label': labels.get(k, k), 'value': v} for k, v in sd.items()]

        twon, tlost, tact, cval = [0] * 12, [0] * 12, [0] * 12, [0.0] * 12
        for p in props:
            if not p.proposal_date:
                continue
            m = p.proposal_date.month - 1
            if p.state in WON:
                twon[m] += 1
                cval[m] += p.total_amount or 0.0
            elif p.state in LOST:
                tlost[m] += 1
            elif p.state in ACTIVE:
                tact[m] += 1
        run, cumulative = 0.0, []
        for v in cval:
            run += v
            cumulative.append(round(run, 2))

        st = {}
        for p in props:
            n = p.service_type_id.name or 'غير محدد'
            st[n] = st.get(n, 0.0) + (p.total_amount or 0.0)
        by_service = [{'label': k, 'value': round(v, 2)}
                      for k, v in sorted(st.items(), key=lambda x: x[1], reverse=True)[:8]]

        slabels = dict(self._fields['pricing_strategy'].selection)
        strat = {}
        for p in props:
            k = p.pricing_strategy or 'manual'
            strat[k] = strat.get(k, 0) + 1
        strategy_dist = [{'label': slabels.get(k, k), 'value': v} for k, v in strat.items()]

        cust = {}
        for p in props:
            n = p.partner_id.name or 'غير محدد'
            r = cust.setdefault(n, {'count': 0, 'amount': 0.0})
            r['count'] += 1
            r['amount'] += p.total_amount or 0.0
        top_customers = [{'name': k, 'amount': round(v['amount'], 2), 'count': v['count']}
                         for k, v in sorted(cust.items(), key=lambda x: x[1]['amount'], reverse=True)[:6]]

        years = sorted({p.proposal_date.year for p in self.search([]) if p.proposal_date}, reverse=True)

        # --- extra KPIs ---
        total_value = sum(props.mapped('total_amount'))
        awarded_value = sum(won.mapped('total_amount'))
        avg_deal = round(awarded_value / len(won), 2) if won else 0.0
        margin_value = round(sum(won.mapped('margin_amount')), 2)
        pending = len(props.filtered(lambda p: p.state in ('submit', 'waiting', 'approve')))
        superseded = len(props.filtered('superseded'))
        today = fields.Date.context_today(self)
        this_month = len(props.filtered(
            lambda p: p.proposal_date and p.proposal_date.year == today.year
            and p.proposal_date.month == today.month))

        # --- by company ---
        # sudo: cross-company dashboard reads company names of proposals whose
        # company may not be in the user's currently-selected companies, which
        # the res.company record rule would otherwise deny (AccessError).
        comp = {}
        for p in props:
            n = p.company_id.sudo().name or '-'
            r = comp.setdefault(n, {'count': 0, 'won': 0})
            r['count'] += 1
            if p.state in WON:
                r['won'] += 1
        by_company = [{'company': k, 'count': v['count'], 'won': v['won']} for k, v in comp.items()]

        # --- margin distribution buckets ---
        buckets = {'<10%': 0, '10-20%': 0, '20-30%': 0, '30-40%': 0, '40%+': 0}
        for p in props:
            m = p.margin_percentage or 0
            if m < 10:
                buckets['<10%'] += 1
            elif m < 20:
                buckets['10-20%'] += 1
            elif m < 30:
                buckets['20-30%'] += 1
            elif m < 40:
                buckets['30-40%'] += 1
            else:
                buckets['40%+'] += 1
        margin_buckets = [{'label': k, 'value': v} for k, v in buckets.items()]

        # --- avg margin by service type ---
        svc_m = {}
        for p in props:
            if not p.margin_percentage:
                continue
            n = p.service_type_id.name or 'غير محدد'
            r = svc_m.setdefault(n, {'sum': 0.0, 'n': 0})
            r['sum'] += p.margin_percentage
            r['n'] += 1
        avg_margin_service = [{'label': k, 'value': round(v['sum'] / v['n'], 1)}
                              for k, v in sorted(svc_m.items(), key=lambda x: x[1]['sum'] / x[1]['n'], reverse=True)[:8]]

        # --- service requests (portal intake) funnel ---
        SR = self.env['proposal.service.request'].sudo()
        sr_labels = dict(SR._fields['state'].selection)
        sr_status = []
        for k in ('new', 'under_review', 'approved', 'quoted', 'declined'):
            sr_status.append({'key': k, 'label': sr_labels.get(k, k),
                              'value': SR.search_count([('state', '=', k)])})
        sr_open = SR.search_count([('state', 'in', ('new', 'under_review', 'approved'))])

        return {
            'years': years,
            'kpi': {
                'total': len(props), 'won': len(won), 'win_rate': win_rate,
                'pipeline_value': round(sum(active.mapped('total_amount')), 2),
                'awarded_value': round(awarded_value, 2),
                'avg_margin': avg_margin,
                'below_guard': len(props.filtered('below_guard')),
                'draft': len(props.filtered(lambda p: p.state == 'draft')),
                'lost': len(lost),
                'total_value': round(total_value, 2),
                'avg_deal': avg_deal,
                'margin_value': margin_value,
                'pending': pending,
                'this_month': this_month,
                'superseded': superseded,
                'sr_open': sr_open,
            },
            'status_dist': status_dist,
            'trend': {'won': twon, 'lost': tlost, 'active': tact},
            'cumulative': cumulative,
            'by_service': by_service,
            'strategy_dist': strategy_dist,
            'top_customers': top_customers,
            'by_company': by_company,
            'margin_buckets': margin_buckets,
            'avg_margin_service': avg_margin_service,
            'sr_status': sr_status,
        }

    def generate_pricing(self):
        # Delete explicitly rather than trusting the (5, 0, 0) command:
        # it says 'unlink all', and unlinking a nullable inverse orphans
        # the rows instead of removing them.
        self.pricing_ids.unlink()
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
            # A zero period silently dropped the whole equipment budget from the
            # price. Refuse instead: an unpriced scrubber is not a rounding
            # error, it is thousands of dinars the customer never pays for.
            if (service_line.id in self.equipment_service_ids.ids
                    and total_equipment_service_qty and not self.proposal_period):
                raise UserError(_(
                    'Set the proposal period before pricing: equipment cost is '
                    'amortised over it, and with no period the equipment would '
                    'be priced at zero.'))
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
                # The daily/monthly selector existed but nothing read it, so a
                # KD 1.000 daily bus card was priced exactly like KD 1.000 a
                # month — under-recovering by a whole working month.
                if getattr(tl, 'period', False) == 'daily':
                    days = getattr(service_line, 'monthly_days', 0) or 26
                    transportation_cost *= days
            # Snapshot-aware (Phase 2/3): use the frozen cost when the line is
            # frozen, else the live catalog cost (effective_* falls back).
            unit_cost = service_line.effective_unit_cost
            individual_cost = unit_cost + material_cost + equipment_cost + transportation_cost
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
                'service_individual_cost': unit_cost,
                'service_total_cost': service_line.effective_total,
                'material_cost': material_cost,
                'equipment_cost': equipment_cost,
                'transportation_cost': transportation_cost,
                'individual_cost': individual_cost,
                'commission_amount': commission_amount,
                'individual_sales_price': individual_cost,
                'cost': (individual_cost + commission_amount) * service_line.quantity,
            }))
        self.write({'pricing_ids': vals, 'total_commission_amount': total_commission})
        # Auto-price using the chosen margin strategy (skip 'manual').
        if self.pricing_strategy and self.pricing_strategy != 'manual':
            self.action_apply_margin()

    def get_commission_amount(self, commission, commission_type, commission_rate, individual_cost):
        commission_amount = 0
        if commission and commission_type and commission_rate:
            if commission_type == 'percentage':
                commission_amount = individual_cost * (commission_rate / 100)
            else:
                commission_amount = commission_rate
        return commission_amount

    # Standing policy: every field change is logged in the chatter.
    _TRACK_EXCLUDE = {
        'id', 'display_name', '__last_update', 'create_date', 'create_uid',
        'write_date', 'write_uid', 'access_token', 'access_url', 'access_warning',
        'qr_image', 'logo', 'barcode', 'qr_url',
    }

    def _setup_complete(self):
        super()._setup_complete()
        for name, field in self._fields.items():
            if name in self._TRACK_EXCLUDE or name.startswith(('message_', 'activity_')):
                continue
            if not getattr(field, 'store', False):
                continue
            if field.type in ('one2many', 'many2many', 'binary'):
                continue
            if not getattr(field, 'tracking', False):
                field.tracking = True

    # create() had no state guard, so the write() gate was defeated by simply
    # creating the record already approved. And Odoo 17 calls create with a
    # LIST, so the old @api.model signature raised AttributeError on any batch
    # import.
    @api.model_create_multi
    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        allowed = (self.env.context.get('proposal_workflow')
                   or self.env.user.has_group('care_proposal.group_proposal_manager'))
        for v in vals_list:
            if v.get('state') in self.WORKFLOW_STATES and not allowed:
                v['state'] = 'draft'
        return self._create_proposals(vals_list)

    def _create_proposals(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', _('New')) == _('New'):
                vals['ref'] = self.env['ir.sequence'].next_by_code(
                    'proposal.proposal') or _('New')
        return super(Proposal, self).create(vals_list)

    def button_submit(self):
        for rec in self:
            # Three proposals in the live data had been sent with a zero total
            # and eight had no service lines at all. A quotation with nothing
            # in it is not a quotation.
            if not rec.partner_id:
                raise UserError(_('Set the customer before submitting.'))
            if not rec.service_ids:
                raise UserError(_('Add at least one service line before submitting.'))
            if not rec.pricing_ids or not (rec.total_amount or 0):
                raise UserError(_(
                    'Generate the pricing before submitting — the total is zero.'))
            if rec.below_guard and not self.env.user.has_group(
                    'care_proposal.group_proposal_manager'):
                raise UserError(_(
                    'Line(s) are below the %s%% margin guard. A proposal manager '
                    'must submit this one.') % rec.margin_guard_pct)
        self._set_state('submit')

    # ---- workflow, enforced on the server -----------------------------
    # `invisible=` in the view is decoration. Every one of these buttons was
    # callable over RPC by any employee, and `state` was a plain writable
    # field, so a junior user could put a proposal straight into 'won' and
    # skip the approval chain entirely. Verified on the live database before
    # this was written.
    WORKFLOW_STATES = ('submit', 'waiting', 'approve', 'reject', 'won', 'cancel')

    def write(self, vals):
        if 'state' in vals and vals['state'] in self.WORKFLOW_STATES \
                and not self.env.context.get('proposal_workflow'):
            if not self.env.user.has_group('care_proposal.group_proposal_manager'):
                raise UserError(_(
                    'The proposal state is set by the approval workflow, not by '
                    'editing the field. Use Submit / Approve / Reject.'))
        return super().write(vals)

    def _set_state(self, state, **extra):
        """The only way the workflow moves a proposal."""
        return super(Proposal, self.with_context(proposal_workflow=True)).write(
            dict(extra, state=state))

    def button_approve(self):
        for rec in self:
            approvers = rec.approval_ids.mapped('user_id')
            if self.env.uid not in approvers.ids and \
                    not self.env.user.has_group('care_proposal.group_proposal_manager'):
                raise UserError(_('You are not an approver on this proposal.'))
            # Nobody signs off their own margin.
            if self.env.uid == rec.create_uid.id and len(approvers) > 1:
                raise UserError(_(
                    'You raised this proposal, so you cannot approve it. '
                    'Another approver on the list must.'))
            if rec.state not in ('submit', 'waiting'):
                raise UserError(_('Only a submitted proposal can be approved.'))
            # A below-cost bid needs a manager, not a click.
            if rec.below_guard and not self.env.user.has_group(
                    'care_proposal.group_proposal_manager'):
                raise UserError(_(
                    'This proposal has line(s) below the margin guard of %s%%. '
                    'A proposal manager must approve it.') % rec.margin_guard_pct)
        self.approval_ids.filtered(lambda l: l.user_id.id == self.env.uid).write({
            'approved': True,
            'date_approved': fields.Datetime.now(),
        })
        if self.approval_ids.filtered(lambda l: not l.approved):
            self._set_state('waiting')
            return
        self._set_state(
            'approve',
            receiver_users=self.env['proposal.receiver'].sudo().search(
                []).mapped('user_id').mapped('id'))

    @api.depends('receiver_users')
    def compute_receiver_users_str(self):
        for rec in self:
            rec.receiver_users_str = ''
            if rec.receiver_users:
                rec.receiver_users_str = ','.join(rec.receiver_users.mapped('email'))

    def button_reject(self):
        self._set_state('reject')

    def button_cancel(self):
        self._set_state('cancel')

    def button_draft(self):
        self._set_state('draft')
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
        self._set_state('won')
        # CRM sync: record winning quote, roll up revenue, mark opportunity won.
        if self.lead_id:
            self.lead_id._sync_won_proposal(self)

    def action_mark_winning(self):
        """Pick this proposal as the winning quotation on its CRM opportunity
        (rolls its amount up to the lead's expected revenue) without changing
        the proposal workflow state."""
        self.ensure_one()
        if not self.lead_id:
            raise UserError(_("This proposal is not linked to a CRM opportunity."))
        self.lead_id.winning_proposal_id = self.id
        self.lead_id.expected_revenue = self.total_amount
        self.message_post(body=_("Marked as the winning proposal for %s.") % self.lead_id.display_name)
        return True

    def action_send_email(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data._xmlid_lookup('care_proposal.email_template_proposal')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data._xmlid_lookup('mail.email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'proposal.proposal',
            'active_model': 'proposal.proposal',
            'model_description': 'Proposal',
            'active_id': self.ids[0],
            'default_res_ids': self.ids,
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

