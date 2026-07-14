# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import fields, models, api, _
from odoo.exceptions import UserError

FREQ = {'weekly': timedelta(weeks=1), 'monthly': timedelta(days=30),
        'quarterly': timedelta(days=90)}


class FacadeZone(models.Model):
    """A façade elevation / panel group and its cleaning frequency."""
    _name = 'care.cafm.facade.zone'
    _description = 'Facade Zone / Elevation'
    _order = 'facility_id, name'

    name = fields.Char(string='الواجهة', required=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True)
    method = fields.Selection([
        ('rope', 'حبال (Rope access)'), ('cradle', 'مهمّة (Cradle/BMU)'), ('waterfed', 'عمود مائي'),
    ], string='الطريقة', default='rope')
    frequency = fields.Selection([
        ('weekly', 'أسبوعي'), ('monthly', 'شهري'), ('quarterly', 'ربع سنوي'),
    ], string='التردّد', default='monthly')
    last_cleaned = fields.Date(string='آخر تنظيف')
    next_due = fields.Date(compute='_compute_due', store=True)
    is_due = fields.Boolean(compute='_compute_due', store=True)
    active = fields.Boolean(default=True)

    @api.depends('last_cleaned', 'frequency')
    def _compute_due(self):
        today = fields.Date.today()
        for z in self:
            base = z.last_cleaned or today
            z.next_due = base + FREQ.get(z.frequency, timedelta(days=30))
            z.is_due = z.next_due <= today


class FacadePermit(models.Model):
    """Height-work permit with wind lockout — no work above the safe wind limit."""
    _name = 'care.cafm.facade.permit'
    _description = 'Height Work Permit'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True, tracking=True)
    zone_id = fields.Many2one('care.cafm.facade.zone', string='الواجهة')
    method = fields.Selection(related='zone_id.method', store=True)
    date = fields.Date(string='التاريخ', default=fields.Date.context_today, required=True)
    valid_hours = fields.Float(string='صلاحية (ساعات)', default=6.0)
    risk_assessed = fields.Boolean(string='تقييم مخاطر مرفق')
    equipment_checked = fields.Boolean(string='فحص المعدّات/الحبال')
    wind_speed = fields.Float(string='سرعة الرياح (كم/س)')
    wind_limit = fields.Float(string='الحدّ الآمن (كم/س)', default=40.0)
    is_safe = fields.Boolean(compute='_compute_safe', store=True)
    supervisor_id = fields.Many2one('res.users', string='مشرف السلامة')
    worker_ids = fields.Many2many('hr.employee', string='العمّال')
    state = fields.Selection([
        ('draft', 'مسودة'), ('submitted', 'مُقدَّم'), ('approved', 'معتمد'),
        ('active', 'قيد التنفيذ'), ('closed', 'مغلق'), ('denied', 'مرفوض'),
    ], default='draft', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('wind_speed', 'wind_limit')
    def _compute_safe(self):
        for p in self:
            p.is_safe = (p.wind_speed or 0.0) <= (p.wind_limit or 40.0)

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', '/') == '/':
                v['name'] = self.env['ir.sequence'].next_by_code('care.cafm.facade.permit') or '/'
        return super().create(vals_list)

    def action_submit(self):
        for p in self:
            if not (p.risk_assessed and p.equipment_checked):
                raise UserError(_('يجب إرفاق تقييم المخاطر وفحص المعدّات قبل التقديم.'))
            p.state = 'submitted'

    def action_approve(self):
        for p in self:
            if not p.is_safe:
                raise UserError(_('⛔ سرعة الرياح تتجاوز الحدّ الآمن — لا يُعتمد العمل على الارتفاع.'))
            p.state = 'approved'

    def action_start(self):
        for p in self:
            if not p.is_safe:
                raise UserError(_('⛔ الرياح غير آمنة — إيقاف العمل.'))
            p.state = 'active'

    def action_close(self):
        for p in self:
            p.state = 'closed'
            if p.zone_id:
                p.zone_id.last_cleaned = fields.Date.today()

    def action_deny(self):
        self.write({'state': 'denied'})
