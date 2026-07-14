from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class Experience(models.Model):
    _name = 'care.experience'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Contract (Experience)'
    _order = 'id desc'

    name = fields.Char(tracking=True)
    line_ids = fields.One2many('care.experience.line', 'experience_id')
    partner_id = fields.Many2one('res.partner', string='Organization', tracking=True)
    contract_amount = fields.Float(tracking=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    period = fields.Integer(string='Period in Months')
    labor_quantity = fields.Integer()
    start_date = fields.Date(tracking=True)
    expire_date = fields.Date(tracking=True)
    contract_type = fields.Selection(selection=[
        ('government', 'Government'),
        ('commercials', 'Commercial / Private'),
    ], tracking=True)
    kanban_state = fields.Selection(selection=[
        ('normal', 'Normal'), ('done', 'Done'), ('blocked', 'Blocked')])
    notes = fields.Text()
    active = fields.Boolean(default=True)
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('submit', 'Submitted'), ('valid', 'Active'),
                   ('under_renewal', 'Under Renewal'), ('expired', 'Expired'),
                   ('terminated', 'Terminated')],
        default="draft", tracking=True)

    # ----- pricing source: commercial → proposal; government → tender
    #   (tender_id is added by the purchase_tender module to avoid a circular
    #    dependency, since purchase_tender depends on care_experience) -----
    proposal_id = fields.Many2one('proposal.proposal', string='Proposal (pricing)')
    pricing_ref = fields.Char(string='Pricing Reference', compute='_compute_pricing', store=True)
    pricing_value = fields.Float(string='Priced Value', compute='_compute_pricing', store=True)

    sequence = fields.Char()
    ref = fields.Char(compute='compute_ref', store=True, string='Contract ID')
    contract_copy = fields.Many2many("ir.attachment", string='Contract Copy')
    project_id = fields.Many2one('project.project', string='Project', store=True)
    department_id = fields.Many2one('hr.department', string='Department', store=True)

    # ----- renewals / guarantees / insurance -----
    renewal_ids = fields.One2many('care.experience.renewal', 'experience_id', string='Renewals')
    renewal_count = fields.Integer(compute='_compute_counts')
    guarantee_ids = fields.One2many('care.bank.guarantee', 'experience_id', string='Bank Guarantees')
    guarantee_count = fields.Integer(compute='_compute_counts')

    # ----- expiry intelligence -----
    days_to_expiry = fields.Integer(compute='_compute_expiry', store=True)
    expiry_state = fields.Selection([
        ('ok', 'Valid'), ('expiring', 'Expiring Soon'), ('expired', 'Expired')],
        compute='_compute_expiry', store=True)
    renew_before = fields.Integer(string='Renew Alert (days before)', default=60)

    # ----- who gets notified -----
    manager_id = fields.Many2one('res.users', string='Contract Owner',
                                 default=lambda s: s.env.user, tracking=True)
    notify_user_ids = fields.Many2many('res.users', string='Notify (alerts & renewals)')

    # ----- insurance (per-contract policy, explicitly tracked like guarantees) -----
    insurance_company = fields.Char(string='شركة التأمين', tracking=True)
    insurance_policy_no = fields.Char(string='رقم الوثيقة', tracking=True)
    insurance_amount = fields.Monetary(string='قيمة التأمين', currency_field='currency_id', tracking=True)
    insurance_start = fields.Date(string='بداية التأمين', tracking=True)
    insurance_expiry = fields.Date(string='انتهاء التأمين', tracking=True)
    insurance_attachment = fields.Many2many('ir.attachment', 'care_exp_insurance_att_rel',
                                            string='وثائق التأمين')
    insurance_days_to_expiry = fields.Integer(compute='_compute_insurance', store=True)
    insurance_state = fields.Selection(
        [('none', 'لا يوجد'), ('ok', 'سارٍ'), ('expiring', 'يقترب من الانتهاء'), ('expired', 'منتهٍ')],
        string='حالة التأمين', compute='_compute_insurance', store=True, default='none')

    @api.depends('insurance_expiry')
    def _compute_insurance(self):
        today = fields.Date.today()
        for rec in self:
            if rec.insurance_expiry:
                rec.insurance_days_to_expiry = (rec.insurance_expiry - today).days
                if rec.insurance_expiry < today:
                    rec.insurance_state = 'expired'
                elif rec.insurance_days_to_expiry <= 30:
                    rec.insurance_state = 'expiring'
                else:
                    rec.insurance_state = 'ok'
            else:
                rec.insurance_days_to_expiry = 0
                rec.insurance_state = 'none'

    @api.depends('contract_type', 'proposal_id', 'proposal_id.total_amount', 'contract_amount')
    def _compute_pricing(self):
        for rec in self:
            if rec.contract_type != 'government' and rec.proposal_id:
                rec.pricing_ref = rec.proposal_id.display_name
                rec.pricing_value = rec.proposal_id.total_amount or rec.contract_amount
            else:
                # government tender pricing is filled by purchase_tender's extension
                if not rec.pricing_ref:
                    rec.pricing_ref = False
                rec.pricing_value = rec.pricing_value or rec.contract_amount

    @api.depends('expire_date', 'renew_before', 'state')
    def _compute_expiry(self):
        today = fields.Date.today()
        for rec in self:
            if rec.expire_date:
                rec.days_to_expiry = (rec.expire_date - today).days
                if rec.expire_date < today:
                    rec.expiry_state = 'expired'
                elif rec.days_to_expiry <= (rec.renew_before or 60):
                    rec.expiry_state = 'expiring'
                else:
                    rec.expiry_state = 'ok'
            else:
                rec.days_to_expiry = 0
                rec.expiry_state = 'ok'

    def _compute_counts(self):
        for rec in self:
            rec.renewal_count = len(rec.renewal_ids)
            rec.guarantee_count = len(rec.guarantee_ids)

    @api.depends('contract_type', 'sequence', 'start_date')
    def compute_ref(self):
        for rec in self:
            year = (rec.start_date or fields.Date.context_today(rec)).year
            code = 'CONT/%s/%s' % ('G' if rec.contract_type == 'government' else 'C', year)
            if rec.sequence:
                code += '/' + str(rec.sequence)
            rec.ref = code

    # ----- state buttons -----
    def button_submit(self):
        if not self.name:
            raise ValidationError(_("Please add contract name!"))
        self.state = 'submit'

    def button_valid(self):
        if not self.name:
            raise ValidationError(_("Please add contract name!"))
        if not self.contract_copy:
            raise ValidationError(_("Please add contract copy!"))
        self.state = 'valid'

    def button_expired(self):
        self.state = 'expired'

    def button_draft(self):
        self.state = 'draft'

    def button_terminate(self):
        self.state = 'terminated'

    # ----- renewal / guarantee quick actions -----
    def action_start_renewal(self):
        self.ensure_one()
        r = self.env['care.experience.renewal'].create({'experience_id': self.id})
        self.state = 'under_renewal'
        return {'type': 'ir.actions.act_window', 'name': _('تجديد/تمديد'),
                'res_model': 'care.experience.renewal', 'res_id': r.id,
                'view_mode': 'form', 'target': 'current'}

    def action_view_renewals(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('التجديدات'),
                'res_model': 'care.experience.renewal', 'view_mode': 'tree,form',
                'domain': [('experience_id', '=', self.id)],
                'context': {'default_experience_id': self.id}}

    def action_view_guarantees(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('الكفالات البنكية'),
                'res_model': 'care.bank.guarantee', 'view_mode': 'tree,form',
                'domain': [('experience_id', '=', self.id)],
                'context': {'default_experience_id': self.id}}

    # ----- crons -----
    @api.model
    def check_experience_expiration(self):
        today = fields.Date.today()
        self.search([('expire_date', '!=', False), ('expire_date', '<', today),
                     ('state', 'not in', ('expired', 'terminated'))]).write({'state': 'expired'})
        # insurance expiry: alert owners for policies expiring within 30 days
        soon = fields.Date.add(today, days=30)
        for c in self.search([('insurance_expiry', '!=', False), ('insurance_expiry', '<=', soon),
                              ('state', 'not in', ('expired', 'terminated'))]):
            users = c.notify_user_ids | c.manager_id
            for u in users:
                if u.partner_id and not c.activity_ids.filtered(
                        lambda a: a.user_id == u and 'تأمين' in (a.summary or '')):
                    c.activity_schedule(
                        'mail.mail_activity_data_todo',
                        summary=_('تجديد تأمين العقد: %s') % (c.name or c.ref),
                        note=_('وثيقة التأمين تنتهي في %s — جدّدها قبل انتهاء الصلاحية.') % c.insurance_expiry,
                        date_deadline=c.insurance_expiry, user_id=u.id)

    @api.model
    def _cron_renewal_reminders(self):
        """Alert owners/notify-users about contracts approaching expiry with no
        active renewal yet."""
        today = fields.Date.today()
        for c in self.search([('state', '=', 'valid'), ('expire_date', '!=', False)]):
            if c.expiry_state != 'expiring':
                continue
            if c.renewal_ids.filtered(lambda r: r.state not in ('signed', 'cancelled')):
                continue
            users = c.notify_user_ids | c.manager_id
            for u in users:
                if u.partner_id:
                    c.activity_schedule(
                        'mail.mail_activity_data_todo',
                        summary=_('تجديد عقد يقترب من الانتهاء: %s') % (c.name or c.ref),
                        note=_('العقد ينتهي خلال %s يوم — ابدأ إجراءات التجديد.') % c.days_to_expiry,
                        user_id=u.id)
