# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PmsPettyCash(models.Model):
    _name = 'care.pms.petty.cash'
    _description = 'Project Petty Cash / Custody'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(string='Reference', default='/', copy=False, readonly=True)
    project_id = fields.Many2one('project.project', string='Project', required=True, index=True, tracking=True)
    manager_id = fields.Many2one('res.users', string='Custodian', default=lambda s: s.env.user, tracking=True)
    assigned_user_ids = fields.Many2many(
        'res.users', 'pms_petty_assigned_rel', 'cash_id', 'user_id',
        string='المكلّفون بالمتابعة/التسوية',
        help='مستخدمون آخرون مصرّح لهم بمتابعة هذه العهدة وتسويتها.')
    # --- disbursement direction (صرف لإدارة / مشروع / شخص) ---
    beneficiary_type = fields.Selection([
        ('department', 'إدارة'), ('project', 'مشروع'), ('person', 'شخص'),
    ], string='صرف إلى', default='project', tracking=True)
    beneficiary_department_id = fields.Many2one('hr.department', string='الإدارة', tracking=True)
    recipient_id = fields.Many2one('res.partner', string='الشخص المستلم', tracking=True)
    reason = fields.Text(string='سبب العهدة', tracking=True)
    request_date = fields.Date(string='تاريخ الطلب', default=fields.Date.today, tracking=True)
    date = fields.Date(string='Opened On', default=fields.Date.today, tracking=True)
    disbursed_date = fields.Date(string='تاريخ الصرف', readonly=True, tracking=True)
    return_date = fields.Date(string='تاريخ الإرجاع', readonly=True, tracking=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    amount = fields.Monetary(string='مبلغ العهدة', tracking=True)
    returned_amount = fields.Monetary(string='المبلغ المُرجَع', readonly=True, tracking=True)
    # --- optional accounting link (draft entries on disburse/return) ---
    journal_id = fields.Many2one('account.journal', string='دفتر الصرف',
                                 default=lambda s: s._default_petty_journal())
    advance_account_id = fields.Many2one('account.account', string='حساب العهدة',
                                         default=lambda s: s._default_petty_advance())
    move_id = fields.Many2one('account.move', string='قيد الصرف', readonly=True, copy=False)
    return_move_id = fields.Many2one('account.move', string='قيد الإرجاع', readonly=True, copy=False)
    move_count = fields.Integer(compute='_compute_move_count')

    @api.model
    def _default_petty_journal(self):
        jid = self.env['ir.config_parameter'].sudo().get_param('care_pms.petty_journal_id')
        return int(jid) if jid else False

    @api.model
    def _default_petty_advance(self):
        aid = self.env['ir.config_parameter'].sudo().get_param('care_pms.petty_advance_account_id')
        return int(aid) if aid else False

    @api.depends('move_id', 'return_move_id')
    def _compute_move_count(self):
        for c in self:
            c.move_count = len([m for m in (c.move_id, c.return_move_id) if m])
    state = fields.Selection([
        ('draft', 'طلب (مسودة)'),
        ('requested', 'طلب مُقدَّم'),
        ('approved', 'معتمد'),
        ('disbursed', 'مصروفة (نشطة)'),
        ('settled', 'تسوية مُقدَّمة'),
        ('closed', 'مغلقة'),
    ], default='draft', tracking=True)
    expense_ids = fields.One2many('care.pms.petty.cash.expense', 'cash_id', string='Expenses')
    settlement_ids = fields.One2many('care.pms.petty.settlement', 'cash_id', string='التسويات')
    settlement_count = fields.Integer(compute='_compute_settlement_count')
    spent = fields.Monetary(string='Spent', compute='_compute_amounts', store=True)
    remaining = fields.Monetary(string='Remaining', compute='_compute_amounts', store=True)
    expense_count = fields.Integer(compute='_compute_amounts')

    @api.depends('expense_ids.amount', 'amount')
    def _compute_amounts(self):
        for c in self:
            c.spent = sum(c.expense_ids.mapped('amount'))
            c.remaining = c.amount - c.spent
            c.expense_count = len(c.expense_ids)

    @api.depends('settlement_ids')
    def _compute_settlement_count(self):
        for c in self:
            c.settlement_count = len(c.settlement_ids)

    def action_new_settlement(self):
        self.ensure_one()
        s = self.env['care.pms.petty.settlement'].create({'cash_id': self.id})
        return {
            'type': 'ir.actions.act_window', 'name': _('تسوية جديدة'),
            'res_model': 'care.pms.petty.settlement', 'res_id': s.id,
            'view_mode': 'form', 'target': 'current',
        }

    def action_view_settlements(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('التسويات'),
            'res_model': 'care.pms.petty.settlement', 'view_mode': 'tree,form',
            'domain': [('cash_id', '=', self.id)],
            'context': {'default_cash_id': self.id},
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.pms.petty.cash') or '/'
        return super().create(vals_list)

    # -------- lifecycle: request → approve → disburse → settle → return & close --------
    def action_request(self):
        for c in self:
            if not c.amount:
                raise UserError(_('حدّد مبلغ العهدة المطلوب قبل تقديم الطلب.'))
            if not c.reason:
                raise UserError(_('اذكر سبب العهدة قبل تقديم الطلب.'))
        self.write({'state': 'requested', 'request_date': fields.Date.today()})

    def action_approve(self):
        self.write({'state': 'approved'})

    def _create_petty_move(self, amount, is_return=False):
        """Create a DRAFT journal entry for a disbursement or a return.
        Skipped silently if accounting isn't configured for the custody."""
        self.ensure_one()
        if 'account.move' not in self.env or not self.journal_id \
                or not self.advance_account_id or not amount or amount <= 0:
            return False
        cash_acc = self.journal_id.default_account_id
        if not cash_acc:
            return False
        adv = self.advance_account_id
        if is_return:
            ref = _('إرجاع عهدة %s') % self.name
            lines = [
                (0, 0, {'account_id': cash_acc.id, 'debit': amount, 'credit': 0.0, 'name': ref}),
                (0, 0, {'account_id': adv.id, 'debit': 0.0, 'credit': amount, 'name': ref}),
            ]
        else:
            ref = _('صرف عهدة %s') % self.name
            lines = [
                (0, 0, {'account_id': adv.id, 'debit': amount, 'credit': 0.0, 'name': ref,
                        'partner_id': self.manager_id.partner_id.id}),
                (0, 0, {'account_id': cash_acc.id, 'debit': 0.0, 'credit': amount, 'name': ref}),
            ]
        return self.env['account.move'].sudo().create({
            'journal_id': self.journal_id.id,
            'date': fields.Date.today(),
            'ref': ref,
            'move_type': 'entry',
            'line_ids': lines,
        })

    def action_view_moves(self):
        self.ensure_one()
        moves = self.move_id | self.return_move_id
        return {
            'type': 'ir.actions.act_window', 'name': _('قيود العهدة'),
            'res_model': 'account.move', 'view_mode': 'tree,form',
            'domain': [('id', 'in', moves.ids)],
        }

    def action_disburse(self):
        """Money is disbursed and credited to the custodian's account."""
        self.write({'state': 'disbursed', 'disbursed_date': fields.Date.today()})
        for c in self:
            if not c.move_id:
                mv = c._create_petty_move(c.amount, is_return=False)
                if mv:
                    c.move_id = mv.id

    def action_settle(self):
        self.write({'state': 'settled'})

    def action_return_close(self):
        """Return the remaining balance and close the custody, documented."""
        for c in self:
            returned = c.remaining
            c.write({
                'state': 'closed',
                'returned_amount': returned,
                'return_date': fields.Date.today(),
            })
            c.message_post(body=_(
                'أُغلقت العهدة — المصروف %s، المُرجَع %s.'
            ) % (c.spent, returned))
            if returned and returned > 0 and not c.return_move_id:
                mv = c._create_petty_move(returned, is_return=True)
                if mv:
                    c.return_move_id = mv.id

    def action_reopen(self):
        self.write({'state': 'disbursed'})

    def action_print(self):
        return self.env.ref('care_pms.action_report_petty_cash').report_action(self)

    def action_print_request(self):
        return self.env.ref('care_pms.action_report_petty_cash_request').report_action(self)

    def action_print_summary(self):
        return self.env.ref('care_pms.action_report_petty_cash_summary').report_action(self)


class PmsPettySettlement(models.Model):
    """One settlement round against a custody. A custody can have several
    settlements over time; each holds its own invoices and total, and the
    custody's remaining balance reflects all of them."""
    _name = 'care.pms.petty.settlement'
    _description = 'Custody Settlement'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(string='المرجع', default='/', copy=False, readonly=True)
    cash_id = fields.Many2one('care.pms.petty.cash', string='العهدة', required=True,
                              ondelete='cascade', index=True, tracking=True)
    project_id = fields.Many2one(related='cash_id.project_id', store=True)
    date = fields.Date(string='تاريخ التسوية', default=fields.Date.today, tracking=True)
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('submitted', 'مقدَّمة'),
        ('approved', 'معتمدة'),
        ('rejected', 'مرفوضة'),
    ], default='draft', tracking=True)
    expense_ids = fields.One2many('care.pms.petty.cash.expense', 'settlement_id', string='الفواتير')
    currency_id = fields.Many2one(related='cash_id.currency_id')
    amount_total = fields.Monetary(string='إجمالي التسوية', compute='_compute_total', store=True)
    cash_remaining = fields.Monetary(related='cash_id.remaining', string='المتبقّي في العهدة')
    move_id = fields.Many2one('account.move', string='قيد التسوية', readonly=True, copy=False)
    note = fields.Text(string='ملاحظات')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('expense_ids.amount')
    def _compute_total(self):
        for s in self:
            s.amount_total = sum(s.expense_ids.mapped('amount'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                cash = self.env['care.pms.petty.cash'].browse(vals.get('cash_id'))
                seq = len(cash.settlement_ids) + 1
                vals['name'] = '%s/T%s' % (cash.name or 'PC', seq)
        return super().create(vals_list)

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        self.write({'state': 'approved'})
        for s in self:
            if not s.move_id:
                mv = s._create_expense_move()
                if mv:
                    s.move_id = mv.id

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_reset(self):
        self.write({'state': 'draft'})

    def _create_expense_move(self):
        """DRAFT entry expensing this settlement against the custody advance:
        Dr Petty Cash Expenses / Cr Employee Custody. Skipped if unconfigured."""
        self.ensure_one()
        cash = self.cash_id
        adv = cash.advance_account_id
        journal = cash.journal_id
        exp_id = self.env['ir.config_parameter'].sudo().get_param('care_pms.petty_expense_account_id')
        if 'account.move' not in self.env or not adv or not journal \
                or not exp_id or not self.amount_total or self.amount_total <= 0:
            return False
        exp_acc = self.env['account.account'].browse(int(exp_id))
        ref = _('تسوية %s') % self.name
        return self.env['account.move'].sudo().create({
            'journal_id': journal.id, 'date': fields.Date.today(), 'ref': ref, 'move_type': 'entry',
            'line_ids': [
                (0, 0, {'account_id': exp_acc.id, 'debit': self.amount_total, 'credit': 0.0, 'name': ref}),
                (0, 0, {'account_id': adv.id, 'debit': 0.0, 'credit': self.amount_total, 'name': ref}),
            ],
        })

    def action_view_move(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('قيد التسوية'),
            'res_model': 'account.move', 'res_id': self.move_id.id, 'view_mode': 'form',
        }

    def action_print(self):
        return self.env.ref('care_pms.action_report_petty_cash').report_action(self)


class PmsPettyCashExpense(models.Model):
    _name = 'care.pms.petty.cash.expense'
    _description = 'Petty Cash Expense'
    _order = 'date desc, id desc'

    cash_id = fields.Many2one('care.pms.petty.cash', string='Petty Cash', required=True,
                              ondelete='cascade', index=True)
    settlement_id = fields.Many2one('care.pms.petty.settlement', string='التسوية',
                                    ondelete='cascade', index=True)
    name = fields.Char(string='Description', required=True)
    invoice_number = fields.Char(string='رقم الفاتورة')
    partner_id = fields.Many2one('res.partner', string='الجهة')
    category = fields.Selection(
        [('maintenance', 'Maintenance'), ('fuel', 'Fuel'), ('transport', 'Transport'),
         ('supplies', 'Supplies'), ('misc', 'Miscellaneous')],
        string='Category', default='misc')
    # --- multi-currency invoice: enter in any currency, convert to KWD ---
    foreign_currency_id = fields.Many2one(
        'res.currency', string='عملة الفاتورة',
        default=lambda s: s.env.company.currency_id)
    foreign_amount = fields.Monetary(string='المبلغ (بعملة الفاتورة)',
                                     currency_field='foreign_currency_id')
    rate = fields.Float(string='سعر الصرف (× للدينار)', default=1.0, digits=(12, 6),
                        help='قيمة الوحدة الواحدة من عملة الفاتورة بالدينار الكويتي.')
    amount = fields.Monetary(string='المبلغ (د.ك)', required=True,
                             help='القيمة بالدينار الكويتي (تُحتسب تلقائياً من المبلغ × سعر الصرف).')
    currency_id = fields.Many2one(related='cash_id.currency_id')
    date = fields.Date(string='Date', default=fields.Date.today)
    attachment = fields.Binary(string='مرفق الفاتورة')
    attachment_name = fields.Char(string='Receipt Name')
    note = fields.Text(string='Condition / Notes')

    @api.onchange('foreign_currency_id', 'date')
    def _onchange_currency_rate(self):
        comp = self.cash_id.currency_id or self.env.company.currency_id
        fc = self.foreign_currency_id or comp
        if fc == comp:
            self.rate = 1.0
        else:
            self.rate = fc._convert(1.0, comp, self.env.company,
                                    self.date or fields.Date.today()) or self.rate or 1.0

    @api.onchange('foreign_amount', 'rate')
    def _onchange_amount_kwd(self):
        self.amount = (self.foreign_amount or 0.0) * (self.rate or 1.0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # keep cash_id in sync when the expense is created under a settlement
            if vals.get('settlement_id') and not vals.get('cash_id'):
                s = self.env['care.pms.petty.settlement'].browse(vals['settlement_id'])
                vals['cash_id'] = s.cash_id.id
        return super().create(vals_list)

    @api.constrains('amount')
    def _check_within_custody(self):
        for exp in self:
            cash = exp.cash_id
            total = sum(cash.expense_ids.mapped('amount'))
            if total > cash.amount:
                raise ValidationError(_(
                    'إجمالي المصروف (%s) يتجاوز قيمة العهدة (%s). لا يمكن الصرف فوق المتبقّي.'
                ) % (total, cash.amount))

    @api.constrains('invoice_number', 'partner_id')
    def _check_unique_invoice(self):
        for exp in self:
            if not (exp.invoice_number and exp.partner_id):
                continue
            dup = self.search([
                ('id', '!=', exp.id),
                ('partner_id', '=', exp.partner_id.id),
                ('invoice_number', '=', exp.invoice_number),
            ], limit=1)
            if dup:
                raise ValidationError(_(
                    'رقم الفاتورة «%s» مُستخدم مسبقاً لنفس الجهة (%s) في العهدة %s.'
                ) % (exp.invoice_number, exp.partner_id.name, dup.cash_id.name))
