# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class CareAllowanceType(models.Model):
    """Allowance catalogue (transport, hardship, meal...) with default
    payment method (inside the payslip vs separate cash payout)."""
    _name = 'care.allowance.type'
    _description = 'Allowance Type'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char()
    default_amount = fields.Monetary()
    payment_method = fields.Selection([
        ('in_payslip', 'Inside Payslip'),
        ('cash', 'Separate Cash Payout'),
    ], default='in_payslip', required=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    active = fields.Boolean(default=True)
    default_frequency = fields.Selection([
        ('once', 'مرة واحدة'), ('daily', 'يومي'), ('weekly', 'أسبوعي'),
        ('monthly', 'شهري'), ('quarterly', 'ربع سنوي'), ('annual', 'سنوي'),
    ], string='التكرار الافتراضي', default='monthly')
    default_scope = fields.Selection([
        ('project', 'خاص بالمشروع فقط'), ('continuous', 'مستمر مع العامل'),
    ], string='النطاق الافتراضي', default='continuous')
    gosi_included = fields.Boolean(string='يدخل في التأمينات (GOSI)')


# frequency → (relativedelta step kwargs, periods per year) for accrual math
FREQ_STEP = {
    'daily': ({'days': 1}, 365.0),
    'weekly': ({'weeks': 1}, 52.0),
    'monthly': ({'months': 1}, 12.0),
    'quarterly': ({'months': 3}, 4.0),
    'annual': ({'years': 1}, 1.0),
    'once': ({}, 1.0),
}


class CareAllowance(models.Model):
    """A granted allowance for a worker. Routed through the approval matrix
    (department manager + senior management depending on amount / method),
    then either reflected in the payslip (CARE_ALLOWANCE) or paid as cash."""
    _name = 'care.allowance'
    _description = 'Worker Allowance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', default='/', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    allowance_type_id = fields.Many2one('care.allowance.type', string='Allowance', tracking=True)
    payment_method = fields.Selection([
        ('in_payslip', 'Inside Payslip'),
        ('cash', 'Separate Cash Payout'),
    ], default='in_payslip', required=True, tracking=True)
    amount = fields.Monetary(required=True, tracking=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    reason = fields.Text(tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('dept', 'Dept. Approved'),
        ('approved', 'Approved'),
        ('done', 'Processed'),
        ('refused', 'Refused'),
    ], default='draft', tracking=True)
    needs_senior = fields.Boolean(compute='_compute_needs_senior', store=True)
    dept_approved_by = fields.Many2one('res.users', readonly=True, copy=False)
    senior_approved_by = fields.Many2one('res.users', readonly=True, copy=False)
    payslip_id = fields.Many2one('hr.payslip', readonly=True, copy=False)
    cash_paid = fields.Boolean(string='Cash Paid', tracking=True, copy=False)
    cash_paid_date = fields.Date(readonly=True, copy=False)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    department_id = fields.Many2one(related='employee_id.department_id', store=True, string='القسم/المشروع')
    payout_id = fields.Many2one('care.allowance.payout', string='طلب الصرف', readonly=True, copy=False, index=True)

    # ----- scope / frequency / accrual -----
    scope = fields.Selection([
        ('project', 'خاص بالمشروع فقط'),
        ('continuous', 'مستمر مع العامل'),
    ], string='نطاق البدل', default='continuous', tracking=True,
        help='«خاص بالمشروع» يتوقف تلقائياً عند نقل العامل لمشروع آخر؛ «مستمر» يبقى مع العامل.')
    frequency = fields.Selection([
        ('once', 'مرة واحدة'), ('daily', 'يومي'), ('weekly', 'أسبوعي'),
        ('monthly', 'شهري'), ('quarterly', 'ربع سنوي'), ('annual', 'سنوي'),
    ], string='التكرار', default='monthly', required=True, tracking=True)
    start_date = fields.Date(string='بداية الاستحقاق', default=fields.Date.context_today, tracking=True)
    end_date = fields.Date(string='نهاية الاستحقاق (اختياري)', tracking=True)
    last_accrual_date = fields.Date(string='آخر استحقاق مصروف', readonly=True, copy=False)
    next_accrual_date = fields.Date(string='تاريخ الاستحقاق القادم',
                                    compute='_compute_accrual', store=True)
    annualized_amount = fields.Monetary(string='القيمة السنوية المكافئة',
                                        compute='_compute_accrual', store=True, currency_field='currency_id')
    # ----- extra options -----
    pro_rated = fields.Boolean(string='حساب تناسبي (Pro-rata)',
                               help='يُحسب المبلغ بالتناسب مع أيام الاستحقاق ضمن الفترة.')
    auto_renew = fields.Boolean(string='تجديد تلقائي', default=True)
    gosi_included = fields.Boolean(string='يدخل في التأمينات (GOSI)')
    taxable = fields.Boolean(string='خاضع للاستقطاع')
    conditional = fields.Boolean(string='مشروط')
    condition_note = fields.Char(string='شرط الاستحقاق')
    max_cap = fields.Monetary(string='حد أقصى تراكمي', currency_field='currency_id')
    project_id = fields.Many2one('project.project', string='المشروع',
                                 related='department_id.project_id', store=True)

    # ----- recurring allowance + stop request (from inside the record) -----
    is_recurring = fields.Boolean(string='بدل متكرر', tracking=True,
                                  compute='_compute_is_recurring', store=True, readonly=False,
                                  help='البدلات المتكررة تُصرف كل فترة حتى يتم إيقافها.')
    stop_state = fields.Selection([
        ('running', 'سارٍ'),
        ('stop_requested', 'طلب إيقاف'),
        ('stopped', 'موقوف'),
        ('resume_requested', 'طلب استمرار'),
    ], default='running', tracking=True, string='حالة الاستمرار')
    stop_reason = fields.Text(string='سبب الإيقاف', tracking=True)
    stop_request_date = fields.Date(string='تاريخ طلب الإيقاف', readonly=True, copy=False)
    stop_requested_by = fields.Many2one('res.users', string='طالب الإيقاف', readonly=True, copy=False)
    stop_effective_date = fields.Date(string='تاريخ الإيقاف الفعلي', tracking=True)
    stop_approved_by = fields.Many2one('res.users', string='معتمد الإيقاف', readonly=True, copy=False)

    def action_request_stop(self):
        """Raise a request to stop this (recurring) allowance — from its own record."""
        for rec in self:
            if rec.stop_state == 'stopped':
                raise UserError(_('هذا البدل موقوف بالفعل.'))
            if not rec.stop_reason:
                raise UserError(_('يرجى كتابة سبب الإيقاف أولاً.'))
            rec.write({'stop_state': 'stop_requested',
                       'stop_request_date': fields.Date.today(),
                       'stop_requested_by': self.env.user.id})
            rec.message_post(body=_('🛑 طلب إيقاف البدل — السبب: %s') % rec.stop_reason)
            mgr = rec.employee_id.department_id.manager_id.user_id
            if mgr:
                rec.activity_schedule('mail.mail_activity_data_todo',
                                      summary=_('طلب إيقاف بدل: %s') % (rec.employee_id.name or ''),
                                      user_id=mgr.id)

    def action_approve_stop(self):
        for rec in self:
            if not rec._is_dept_manager():
                raise UserError(_('يعتمد الإيقاف مدير القسم أو مدير الموارد البشرية فقط.'))
            rec.write({'stop_state': 'stopped',
                       'stop_effective_date': rec.stop_effective_date or fields.Date.today(),
                       'stop_approved_by': self.env.user.id})
            rec.message_post(body=_('✅ تم اعتماد إيقاف البدل اعتباراً من %s.') % rec.stop_effective_date)

    def action_reject_stop(self):
        for rec in self:
            rec.write({'stop_state': 'running', 'stop_request_date': False,
                       'stop_requested_by': False})
            rec.message_post(body=_('↩️ رُفض طلب إيقاف البدل — يستمر الصرف.'))

    # ----- resume after stop (from inside the record) -----
    def action_request_resume(self):
        for rec in self:
            if rec.stop_state != 'stopped':
                raise UserError(_('لا يمكن طلب الاستمرار إلا لبدل موقوف.'))
            rec.write({'stop_state': 'resume_requested'})
            rec.message_post(body=_('▶️ طلب استمرار/إعادة تفعيل البدل الموقوف.'))
            mgr = rec.employee_id.department_id.manager_id.user_id
            if mgr:
                rec.activity_schedule('mail.mail_activity_data_todo',
                                      summary=_('طلب استمرار بدل: %s') % (rec.employee_id.name or ''),
                                      user_id=mgr.id)

    def action_approve_resume(self):
        for rec in self:
            if not rec._is_dept_manager():
                raise UserError(_('يعتمد الاستمرار مدير القسم أو مدير الموارد البشرية فقط.'))
            rec.write({'stop_state': 'running', 'stop_effective_date': False,
                       'stop_reason': False, 'stop_request_date': False, 'stop_requested_by': False})
            rec.message_post(body=_('✅ تم اعتماد استمرار البدل — يُستأنف الصرف.'))

    @api.depends('frequency')
    def _compute_is_recurring(self):
        for rec in self:
            rec.is_recurring = rec.frequency not in (False, 'once')

    @api.depends('frequency', 'start_date', 'last_accrual_date', 'amount', 'end_date',
                 'stop_state', 'cash_paid_date')
    def _compute_accrual(self):
        for rec in self:
            step, per_year = FREQ_STEP.get(rec.frequency or 'monthly', ({'months': 1}, 12.0))
            rec.annualized_amount = (rec.amount or 0.0) * per_year
            # next due date = last accrual + one period, else the start date
            if rec.stop_state == 'stopped' or rec.frequency == 'once':
                nxt = rec.start_date if (rec.frequency == 'once' and not rec.cash_paid_date) else False
            else:
                base = rec.last_accrual_date or rec.cash_paid_date or rec.start_date
                if base and step:
                    nxt = base + relativedelta(**step) if rec.last_accrual_date or rec.cash_paid_date else base
                else:
                    nxt = rec.start_date
            if nxt and rec.end_date and nxt > rec.end_date:
                nxt = False
            rec.next_accrual_date = nxt

    @api.depends('amount', 'payment_method')
    def _compute_needs_senior(self):
        ICP = self.env['ir.config_parameter'].sudo()
        threshold = float(ICP.get_param('care_hr.allowance_senior_threshold') or 0.0)
        for rec in self:
            rec.needs_senior = (rec.payment_method == 'cash') or \
                (threshold and rec.amount > threshold)

    @api.onchange('allowance_type_id')
    def _onchange_type(self):
        if self.allowance_type_id:
            t = self.allowance_type_id
            self.amount = t.default_amount
            self.payment_method = t.payment_method
            self.frequency = t.default_frequency or 'monthly'
            self.scope = t.default_scope or 'continuous'
            self.gosi_included = t.gosi_included

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.allowance') or '/'
        return super().create(vals_list)

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_('Allowance amount must be positive.'))

    def action_submit(self):
        self.write({'state': 'submitted'})

    def _is_dept_manager(self):
        self.ensure_one()
        mgr = self.employee_id.department_id.manager_id.user_id
        return self.env.user == mgr or self.env.user.has_group('hr.group_hr_manager')

    def action_dept_approve(self):
        for rec in self:
            if not rec._is_dept_manager():
                raise UserError(_('Only the department manager (or HR Manager) can approve this step.'))
            if rec.needs_senior:
                rec.write({'state': 'dept', 'dept_approved_by': self.env.user.id})
            else:
                rec.write({'state': 'approved', 'dept_approved_by': self.env.user.id})

    def action_senior_approve(self):
        for rec in self:
            if not self.env.user.has_group('care_hr.group_care_senior_approver'):
                raise UserError(_('Only a Senior Approver (Top Management) can approve this step.'))
            rec.write({'state': 'approved', 'senior_approved_by': self.env.user.id})

    def action_refuse(self):
        self.write({'state': 'refused'})

    def action_reset(self):
        self.write({'state': 'draft', 'dept_approved_by': False, 'senior_approved_by': False})

    def action_mark_cash_paid(self):
        for rec in self:
            if rec.payment_method != 'cash' or rec.state != 'approved':
                raise UserError(_('Only approved cash allowances can be marked paid.'))
            rec.write({'cash_paid': True, 'cash_paid_date': fields.Date.today(), 'state': 'done'})
