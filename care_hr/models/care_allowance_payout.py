# -*- coding: utf-8 -*-
# Allowance disbursement request ("طلب صرف البدلات"): a payroll-side batch that
# collects worker allowances for a period (filtered by project/worker/type),
# shows who was paid vs not, picks a payment method, prints PDF + Excel, and is
# sent to Finance for payment.
from markupsafe import Markup
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class CareAllowancePayout(models.Model):
    _name = 'care.allowance.payout'
    _description = 'Allowance Disbursement Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='المرجع', default='/', copy=False, readonly=True)
    date = fields.Date(string='تاريخ الطلب', default=fields.Date.context_today, required=True, tracking=True)

    # ---- period + filters used to collect entitlements ----
    date_from = fields.Date(string='من تاريخ', required=True, tracking=True,
                            default=lambda s: fields.Date.today().replace(day=1))
    date_to = fields.Date(string='إلى تاريخ', required=True, tracking=True,
                          default=fields.Date.context_today)
    department_id = fields.Many2one('hr.department', string='القسم/المشروع', tracking=True)
    employee_id = fields.Many2one('hr.employee', string='العامل', tracking=True)
    allowance_type_id = fields.Many2one('care.allowance.type', string='نوع الاستحقاق', tracking=True)
    only_unpaid = fields.Boolean(string='غير المصروف فقط', default=True,
                                 help='عند التجميع، أحضر البدلات التي لم تُصرف بعد فقط.')

    payment_method = fields.Selection([
        ('cash', 'نقدي (كاش)'),
        ('bank', 'تحويل بنكي'),
        ('cheque', 'شيك'),
        ('link', 'رابط دفع'),
    ], string='طريقة الدفع', default='bank', required=True, tracking=True)

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('collected', 'تم التجميع'),
        ('sent_finance', 'أُرسل للمالية'),
        ('paid', 'تم الصرف'),
        ('cancelled', 'ملغى'),
    ], default='draft', tracking=True)

    line_ids = fields.One2many('care.allowance.payout.line', 'payout_id', string='البنود')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    finance_note = fields.Text(string='ملاحظات للمالية')
    sent_finance_date = fields.Date(readonly=True, copy=False)
    paid_date = fields.Date(readonly=True, copy=False)

    # ---- computed totals ----
    total_amount = fields.Monetary(compute='_compute_totals', store=True, string='إجمالي المبلغ')
    to_pay_amount = fields.Monetary(compute='_compute_totals', store=True, string='المطلوب صرفه')
    line_count = fields.Integer(compute='_compute_totals', store=True, string='عدد البنود')
    paid_count = fields.Integer(compute='_compute_totals', store=True, string='مصروف')
    unpaid_count = fields.Integer(compute='_compute_totals', store=True, string='غير مصروف')

    @api.depends('line_ids', 'line_ids.amount', 'line_ids.to_pay', 'line_ids.is_paid')
    def _compute_totals(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)
            rec.total_amount = sum(rec.line_ids.mapped('amount'))
            rec.to_pay_amount = sum(l.amount for l in rec.line_ids if l.to_pay and not l.is_paid)
            rec.paid_count = len(rec.line_ids.filtered('is_paid'))
            rec.unpaid_count = len(rec.line_ids.filtered(lambda l: not l.is_paid))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.allowance.payout') or '/'
        return super().create(vals_list)

    def _collect_domain(self):
        self.ensure_one()
        dom = [('date', '>=', self.date_from), ('date', '<=', self.date_to),
               ('state', 'in', ('approved', 'done'))]
        if self.department_id:
            dom.append(('department_id', '=', self.department_id.id))
        if self.employee_id:
            dom.append(('employee_id', '=', self.employee_id.id))
        if self.allowance_type_id:
            dom.append(('allowance_type_id', '=', self.allowance_type_id.id))
        return dom

    def action_collect(self):
        """Pull matching allowances into lines (who's paid / who isn't)."""
        for rec in self:
            allowances = self.env['care.allowance'].search(rec._collect_domain())
            # a payslip-processed or cash-paid allowance counts as already paid
            existing = rec.line_ids.mapped('allowance_id')
            new_lines = []
            for a in allowances:
                if a in existing:
                    continue
                is_paid = bool(a.cash_paid) or a.state == 'done'
                # honor the "only unpaid" filter
                if rec.only_unpaid and is_paid:
                    continue
                # don't grab allowances already inside another open payout
                if a.payout_id and a.payout_id != rec:
                    continue
                new_lines.append((0, 0, {
                    'allowance_id': a.id,
                    'is_paid': is_paid,
                    'to_pay': not is_paid,
                }))
            rec.line_ids = new_lines
            rec.state = 'collected'
            rec.message_post(body=_('تم تجميع %s بند للفترة %s ← %s.') % (
                len(new_lines), rec.date_from, rec.date_to))

    def action_send_finance(self):
        for rec in self:
            if not rec.line_ids.filtered(lambda l: l.to_pay and not l.is_paid):
                raise UserError(_('لا توجد بنود مطلوب صرفها. جمّع البدلات أولاً.'))
            rec.write({'state': 'sent_finance', 'sent_finance_date': fields.Date.today()})
            rec.line_ids.filtered(lambda l: l.to_pay).mapped('allowance_id').write({'payout_id': rec.id})
            finance = self.env.ref('care_hr.group_care_senior_approver', raise_if_not_found=False)
            partners = finance.users.mapped('partner_id') if finance else self.env['res.partner']
            method = dict(self._fields['payment_method'].selection).get(rec.payment_method)
            body = Markup(
                '<p>طلب صرف بدلات <b>%s</b> بانتظار الدفع.</p>'
                '<ul><li>الفترة: %s ← %s</li><li>عدد البنود: %s</li>'
                '<li>المبلغ المطلوب: <b>%s %s</b></li><li>طريقة الدفع: %s</li></ul>'
            ) % (rec.name, rec.date_from, rec.date_to, len(rec.line_ids),
                 '{:,.3f}'.format(rec.to_pay_amount), rec.currency_id.name or '', method)
            rec.message_post(body=body, partner_ids=partners.ids,
                             subject=_('صرف بدلات للدفع: %s') % rec.name,
                             message_type='notification', subtype_xmlid='mail.mt_comment')

    def action_mark_paid(self):
        for rec in self:
            paid_lines = rec.line_ids.filtered(lambda l: l.to_pay and not l.is_paid)
            paid_lines.write({'is_paid': True})
            paid_lines.mapped('allowance_id').write({
                'cash_paid': True, 'cash_paid_date': fields.Date.today(), 'state': 'done'})
            rec.write({'state': 'paid', 'paid_date': fields.Date.today()})
            rec.message_post(body=_('💰 تم صرف %s بند بمبلغ %s %s.') % (
                len(paid_lines), '{:,.3f}'.format(sum(paid_lines.mapped('amount'))),
                rec.currency_id.name or ''))

    def action_cancel(self):
        self.mapped('line_ids.allowance_id').write({'payout_id': False})
        self.write({'state': 'cancelled'})

    def action_reset(self):
        self.write({'state': 'draft'})

    def action_print_pdf(self):
        return self.env.ref('care_hr.action_report_allowance_payout').report_action(self)

    def action_export_xlsx(self):
        return self.env.ref('care_hr.action_report_allowance_payout_xlsx').report_action(self)


class CareAllowancePayoutLine(models.Model):
    _name = 'care.allowance.payout.line'
    _description = 'Allowance Disbursement Line'
    _order = 'employee_id, id'

    payout_id = fields.Many2one('care.allowance.payout', required=True, ondelete='cascade', index=True)
    allowance_id = fields.Many2one('care.allowance', required=True, ondelete='restrict')
    employee_id = fields.Many2one(related='allowance_id.employee_id', store=True, string='العامل')
    department_id = fields.Many2one(related='allowance_id.department_id', store=True, string='القسم/المشروع')
    allowance_type_id = fields.Many2one(related='allowance_id.allowance_type_id', store=True, string='نوع الاستحقاق')
    allowance_date = fields.Date(related='allowance_id.date', store=True, string='تاريخ الاستحقاق')
    amount = fields.Monetary(related='allowance_id.amount', store=True, string='المبلغ')
    currency_id = fields.Many2one(related='allowance_id.currency_id')
    is_paid = fields.Boolean(string='مصروف', help='صُرف مسبقاً (نقداً أو عبر القسيمة).')
    to_pay = fields.Boolean(string='يُصرف', default=True)
    pay_status = fields.Selection([('paid', 'مصروف'), ('unpaid', 'غير مصروف')],
                                  compute='_compute_pay_status', store=True)

    @api.depends('is_paid')
    def _compute_pay_status(self):
        for l in self:
            l.pay_status = 'paid' if l.is_paid else 'unpaid'
