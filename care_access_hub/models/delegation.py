# -*- coding: utf-8 -*-
# التفويضات (الإنابة): المستخدم يفوّض مستخدمًا آخر في اعتماداته — كل الموديولات أو مخصّص —
# بين تاريخَي بداية ونهاية وبحدّ مبلغ. المفوَّض إليه يعتمد بتوقيعه مع «مفوّض من قبل...».
from odoo import api, fields, models, _


class CareUserDelegation(models.Model):
    _name = 'care.user.delegation'
    _description = 'تفويض صلاحيات اعتماد'
    _order = 'date_from desc, id desc'

    delegator_id = fields.Many2one('res.users', string='المفوِّض', required=True,
                                   default=lambda s: s.env.user, ondelete='cascade', index=True)
    delegate_id = fields.Many2one('res.users', string='المفوَّض إليه', required=True,
                                  domain=[('share', '=', False)], ondelete='cascade')
    scope = fields.Selection([('all', 'كل الموديولات'), ('custom', 'مخصّص')],
                             string='النطاق', default='all', required=True)
    line_ids = fields.One2many('care.user.delegation.line', 'delegation_id', string='الأنواع المفوّضة')
    date_from = fields.Date(string='من تاريخ', default=fields.Date.context_today)
    date_to = fields.Date(string='إلى تاريخ')
    amount_limit = fields.Float(string='حدّ المبلغ (0 = بلا حد)')
    active = fields.Boolean(default=True)
    state = fields.Selection(
        [('off', 'موقوف'), ('sched', 'مجدول'), ('active', 'فعّال'), ('expired', 'منتهٍ')],
        string='الحالة', compute='_compute_state')

    @api.depends('active', 'date_from', 'date_to')
    def _compute_state(self):
        today = fields.Date.today()
        for d in self:
            if not d.active:
                d.state = 'off'
            elif d.date_from and d.date_from > today:
                d.state = 'sched'
            elif d.date_to and d.date_to < today:
                d.state = 'expired'
            else:
                d.state = 'active'

    def action_load_types(self):
        """يملأ قائمة الأنواع (أيقونة + مفتاح تفويض) للنطاق المخصّص."""
        AT = self.env.get('care.approval.type')
        Line = self.env['care.user.delegation.line'].sudo()
        for d in self:
            if AT is None:
                continue
            existing = set(d.line_ids.mapped('type_id').ids)
            rows = [{'delegation_id': d.id, 'type_id': t.id, 'enabled': False}
                    for t in AT.sudo().search([]) if t.id not in existing]
            if rows:
                Line.create(rows)
        return True

    def covers_type(self, approval_type):
        """هل يشمل هذا التفويض نوع الاعتماد المُعطى (ضمن المدّة والتفعيل)؟"""
        self.ensure_one()
        if self.state != 'active':
            return False
        if self.scope == 'all':
            return True
        return approval_type.id in self.line_ids.filtered('enabled').mapped('type_id').ids


class CareUserDelegationLine(models.Model):
    _name = 'care.user.delegation.line'
    _description = 'نوع مفوّض'
    _order = 'type_name'

    delegation_id = fields.Many2one('care.user.delegation', required=True, ondelete='cascade')
    type_id = fields.Many2one('care.approval.type', string='نوع الاعتماد', required=True)
    type_name = fields.Char(related='type_id.name', store=True)
    enabled = fields.Boolean(string='مفوَّض', default=False)

    _sql_constraints = [('deleg_type_uniq', 'unique(delegation_id, type_id)', 'مُعرَّف مسبقًا.')]
