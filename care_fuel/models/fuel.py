# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CareFuelCard(models.Model):
    _name = 'care.fuel.card'
    _description = 'بطاقة وقود مسبقة الدفع'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(string='رقم البطاقة', required=True, tracking=True, index=True)
    provider = fields.Char(string='الجهة المُصدِرة', tracking=True)
    project_id = fields.Many2one('project.project', string='المشروع', index=True, tracking=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='المركبة المخصّصة', tracking=True)
    driver_id = fields.Many2one('hr.employee', string='السائق المسؤول', tracking=True)

    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    initial_balance = fields.Monetary(string='الرصيد الافتتاحي', tracking=True)
    topup_total = fields.Monetary(string='إجمالي الشحن', compute='_compute_balance', store=True)
    consumed = fields.Monetary(string='المستهلك', compute='_compute_balance', store=True)
    balance = fields.Monetary(string='الرصيد المتاح', compute='_compute_balance', store=True)

    topup_ids = fields.One2many('care.fuel.card.topup', 'card_id', string='عمليات الشحن')
    entry_ids = fields.One2many('care.fuel.entry', 'card_id', string='عمليات التعبئة')
    entry_count = fields.Integer(compute='_compute_counts')

    state = fields.Selection([('active', 'فعّالة'), ('blocked', 'موقوفة')],
                             default='active', string='الحالة', tracking=True)
    note = fields.Char(string='ملاحظات')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('initial_balance', 'topup_ids.amount', 'entry_ids.amount', 'entry_ids.state', 'entry_ids.method')
    def _compute_balance(self):
        for card in self:
            tt = sum(card.topup_ids.mapped('amount'))
            used = sum(e.amount for e in card.entry_ids
                       if e.method == 'card' and e.state == 'confirmed')
            card.topup_total = tt
            card.consumed = used
            card.balance = (card.initial_balance or 0.0) + tt - used

    def _compute_counts(self):
        for card in self:
            card.entry_count = len(card.entry_ids)

    def action_view_entries(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('عمليات التعبئة'),
            'res_model': 'care.fuel.entry', 'view_mode': 'tree,form',
            'domain': [('card_id', '=', self.id)],
            'context': {'default_card_id': self.id, 'default_method': 'card'},
        }


class CareFuelCardTopup(models.Model):
    _name = 'care.fuel.card.topup'
    _description = 'شحن بطاقة وقود'
    _order = 'date desc, id desc'

    card_id = fields.Many2one('care.fuel.card', string='البطاقة', required=True,
                              ondelete='cascade', index=True)
    date = fields.Date(string='التاريخ', default=fields.Date.context_today, required=True)
    amount = fields.Monetary(string='مبلغ الشحن', required=True)
    currency_id = fields.Many2one(related='card_id.currency_id')
    reference = fields.Char(string='المرجع / الإيصال')
    note = fields.Char(string='ملاحظة')


class CareFuelEntry(models.Model):
    _name = 'care.fuel.entry'
    _description = 'عملية تعبئة وقود'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    # substantive fields locked once a newer entry exists for the same scope
    _LOCKED = {'date', 'project_id', 'vehicle_id', 'driver_id', 'method', 'card_id',
               'petty_cash_id', 'amount', 'liters', 'odometer', 'station'}

    name = fields.Char(string='المرجع', default='/', copy=False, readonly=True, index=True)
    date = fields.Datetime(string='التاريخ والوقت', default=fields.Datetime.now, required=True, tracking=True)
    project_id = fields.Many2one('project.project', string='المشروع', index=True, tracking=True)
    department_id = fields.Many2one('hr.department', related='project_id.pms_department_id',
                                    string='القسم', store=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='المركبة', tracking=True)
    driver_id = fields.Many2one('hr.employee', string='السائق', tracking=True)

    method = fields.Selection([('card', 'بطاقة مسبقة الدفع'), ('cash', 'عهدة نقدية')],
                              string='طريقة الدفع', required=True, default='card', tracking=True)
    card_id = fields.Many2one('care.fuel.card', string='بطاقة الوقود', tracking=True)
    petty_cash_id = fields.Many2one('care.pms.petty.cash', string='العهدة النقدية', tracking=True)

    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    amount = fields.Monetary(string='المبلغ', required=True, tracking=True)
    liters = fields.Float(string='اللترات', tracking=True)
    price_per_liter = fields.Float(string='سعر اللتر', compute='_compute_ppl', store=True)
    odometer = fields.Float(string='قراءة العدّاد', tracking=True)
    station = fields.Char(string='المحطة')

    receipt = fields.Binary(string='صورة الإيصال', attachment=True)
    receipt_filename = fields.Char(string='اسم الملف')
    note = fields.Text(string='ملاحظات')

    state = fields.Selection([('draft', 'مسودة'), ('confirmed', 'مؤكّدة')],
                             default='draft', string='الحالة', tracking=True, index=True)
    is_latest = fields.Boolean(string='آخر تسجيل', compute='_compute_is_latest')
    created_by = fields.Many2one('res.users', string='سجّلها', default=lambda s: s.env.user,
                                 readonly=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('amount', 'liters')
    def _compute_ppl(self):
        for rec in self:
            rec.price_per_liter = (rec.amount / rec.liters) if rec.liters else 0.0

    def _compute_is_latest(self):
        for rec in self:
            if not rec.id or isinstance(rec.id, models.NewId):
                rec.is_latest = True
                continue
            base = [('id', '!=', rec.id)]
            if rec.project_id:
                base.append(('project_id', '=', rec.project_id.id))
            if rec.vehicle_id:
                base.append(('vehicle_id', '=', rec.vehicle_id.id))
            later = self.sudo().search_count(base + [
                '|', ('date', '>', rec.date),
                '&', ('date', '=', rec.date), ('id', '>', rec.id)])
            rec.is_latest = later == 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.fuel.entry') or '/'
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.context.get('fuel_bypass_lock') and (set(vals) & self._LOCKED):
            for rec in self:
                if not rec.is_latest:
                    raise UserError(_(
                        'لا يمكن تعديل هذه العملية بعد تسجيل عملية تعبئة أحدث منها لنفس المركبة/المشروع. '
                        'يُسمح بتعديل آخر عملية فقط.'))
        return super().write(vals)

    @api.constrains('method', 'card_id')
    def _check_card(self):
        for rec in self:
            if rec.method == 'card' and not rec.card_id:
                raise UserError(_('اختر بطاقة الوقود عند الدفع بالبطاقة.'))

    def action_confirm(self):
        for rec in self:
            if rec.method == 'card' and not rec.card_id:
                raise UserError(_('اختر بطاقة الوقود أولًا.'))
            rec.state = 'confirmed'

    def action_draft(self):
        for rec in self:
            if not rec.is_latest:
                raise UserError(_('لا يمكن إعادة عملية قديمة إلى مسودة.'))
            rec.state = 'draft'

    def action_print(self):
        return self.env.ref('care_fuel.action_report_fuel_entry').report_action(self)
