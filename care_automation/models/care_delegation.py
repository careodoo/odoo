# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class CareDelegation(models.Model):
    """Authority delegation (mockup 82): a manager delegates a specific
    approval scope to a delegate for a bounded period, so approvals continue
    during absence. Every delegated decision is stamped with both names and the
    delegation auto-expires — no work stoppage, no lost accountability."""
    _name = 'care.delegation'
    _description = 'Authority Delegation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_end desc, id desc'

    name = fields.Char(string='المرجع', default='/', copy=False, readonly=True)
    delegator_id = fields.Many2one(
        'res.users', string='المفوِّض (من)', required=True, tracking=True,
        default=lambda self: self.env.user)
    delegate_id = fields.Many2one(
        'res.users', string='المفوَّض إليه', required=True, tracking=True)
    scope = fields.Selection([
        ('payroll_final', 'اعتماد الرواتب النهائي'),
        ('leave', 'اعتماد الإجازات'),
        ('overtime', 'اعتماد الأوفر تايم'),
        ('loan', 'اعتماد السلف'),
        ('expense', 'اعتماد المصاريف'),
        ('gov', 'المعاملات الحكومية'),
        ('all', 'كل الصلاحيات'),
    ], string='الصلاحية', required=True, default='leave', tracking=True)
    reason = fields.Char(string='السبب', help='مثال: إجازة المدير', tracking=True)
    date_start = fields.Date(string='من تاريخ', default=fields.Date.context_today, tracking=True)
    date_end = fields.Date(string='إلى تاريخ', tracking=True)
    until_notice = fields.Boolean(string='حتى إشعار', tracking=True)
    delegated_count = fields.Integer(string='اعتمادات تمّت بالإنابة', default=0, readonly=True)
    is_current = fields.Boolean(string='سارية الآن', compute='_compute_is_current',
                                search='_search_is_current')
    ends_soon = fields.Boolean(string='تنتهي هذا الأسبوع', compute='_compute_is_current')
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('pending', 'بانتظار موافقة الإدارة'),
        ('active', 'نشط'),
        ('expired', 'منتهٍ'),
        ('revoked', 'مسترد'),
    ], string='الحالة', default='draft', tracking=True)
    note = fields.Text(string='ملاحظات')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('state', 'date_start', 'date_end', 'until_notice')
    def _compute_is_current(self):
        today = fields.Date.today()
        week = today + timedelta(days=7)
        for rec in self:
            in_window = (
                (not rec.date_start or rec.date_start <= today)
                and (rec.until_notice or not rec.date_end or rec.date_end >= today))
            rec.is_current = rec.state == 'active' and in_window
            rec.ends_soon = bool(
                rec.state == 'active' and not rec.until_notice
                and rec.date_end and today <= rec.date_end <= week)

    def _search_is_current(self, operator, value):
        today = fields.Date.today()
        ids = self.search([
            ('state', '=', 'active'),
            '|', ('date_start', '=', False), ('date_start', '<=', today),
        ]).filtered(lambda r: r.until_notice or not r.date_end or r.date_end >= today).ids
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [('id', 'in', ids)]
        return [('id', 'not in', ids)]

    @api.constrains('date_start', 'date_end', 'until_notice')
    def _check_dates(self):
        for rec in self:
            if not rec.until_notice and rec.date_end and rec.date_start and rec.date_end < rec.date_start:
                raise UserError(_('تاريخ الانتهاء يجب أن يكون بعد تاريخ البدء.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.delegation') or '/'
        return super().create(vals_list)

    def action_submit(self):
        self.write({'state': 'pending'})

    def action_approve(self):
        if not self.env.user.has_group('hr.group_hr_manager'):
            raise UserError(_('موافقة الإدارة العليا مطلوبة: فقط مدير الموارد البشرية يعتمد التفويض.'))
        self.write({'state': 'active'})

    def action_revoke(self):
        self.write({'state': 'revoked'})

    def action_reset(self):
        self.write({'state': 'draft'})

    @api.model
    def _cron_expire(self):
        today = fields.Date.today()
        self.search([
            ('state', '=', 'active'), ('until_notice', '=', False),
            ('date_end', '!=', False), ('date_end', '<', today),
        ]).write({'state': 'expired'})

    @api.model
    def get_active_delegate(self, delegator_user_id, scope):
        """Helper: return the current delegate user for a delegator+scope, if any."""
        deleg = self.search([
            ('delegator_id', '=', delegator_user_id),
            ('scope', 'in', (scope, 'all')),
            ('is_current', '=', True),
        ], limit=1)
        return deleg.delegate_id.id if deleg else False
