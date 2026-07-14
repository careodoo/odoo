# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import fields, models, api, _
from odoo.exceptions import UserError

FREQ_DELTA = {'hourly': timedelta(hours=1), 'daily': timedelta(days=1),
              'weekly': timedelta(weeks=1), 'monthly': timedelta(days=30)}


# ============ AUDIT TEMPLATE ============
class CleanAuditTemplate(models.Model):
    _name = 'care.cafm.clean.audit.template'
    _description = 'Cleaning Audit Checklist Template'
    _order = 'name'

    name = fields.Char(string='القالب', required=True)
    item_ids = fields.One2many('care.cafm.clean.audit.item', 'template_id', string='بنود الفحص')
    active = fields.Boolean(default=True)


class CleanAuditItem(models.Model):
    _name = 'care.cafm.clean.audit.item'
    _description = 'Audit Checklist Item'
    _order = 'sequence, id'

    template_id = fields.Many2one('care.cafm.clean.audit.template', required=True, ondelete='cascade')
    name = fields.Char(string='البند', required=True)
    weight = fields.Integer(string='الوزن', default=1)
    sequence = fields.Integer(default=10)


# ============ AUDIT ============
class CleanAudit(models.Model):
    _name = 'care.cafm.clean.audit'
    _description = 'Cleaning Quality Audit'
    _inherit = ['mail.thread']
    _order = 'audit_date desc, id desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True, tracking=True)
    location_id = fields.Many2one('care.cafm.location', string='الموقع', tracking=True,
                                  domain="[('facility_id','=',facility_id)]")
    template_id = fields.Many2one('care.cafm.clean.audit.template', string='قالب الفحص')
    auditor_id = fields.Many2one('res.users', string='المدقّق', default=lambda s: s.env.user)
    audit_date = fields.Datetime(string='التاريخ', default=fields.Datetime.now, required=True)
    line_ids = fields.One2many('care.cafm.clean.audit.line', 'audit_id', string='البنود')
    score = fields.Float(string='الدرجة %', compute='_compute_score', store=True)
    rating = fields.Selection([
        ('excellent', 'ممتاز'), ('good', 'جيد'), ('fair', 'مقبول'), ('poor', 'ضعيف'),
    ], compute='_compute_score', store=True, string='التقييم')
    fail_count = fields.Integer(compute='_compute_score', store=True)
    state = fields.Selection([('draft', 'مسودة'), ('done', 'منتهٍ')], default='draft', tracking=True)
    client_ack = fields.Selection([
        ('pending', 'بانتظار'), ('accepted', 'مقبول من العميل'), ('disputed', 'معترض عليه'),
    ], string='إقرار العميل', default='pending', tracking=True)
    client_ack_comment = fields.Char(string='تعليق العميل', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('line_ids', 'line_ids.result', 'line_ids.weight')
    def _compute_score(self):
        for a in self:
            graded = a.line_ids.filtered(lambda l: l.result in ('pass', 'fail'))
            tot = sum(graded.mapped('weight')) or 0
            passed = sum(graded.filtered(lambda l: l.result == 'pass').mapped('weight'))
            a.score = (100.0 * passed / tot) if tot else 0.0
            a.fail_count = len(a.line_ids.filtered(lambda l: l.result == 'fail'))
            a.rating = ('excellent' if a.score >= 90 else 'good' if a.score >= 75
                        else 'fair' if a.score >= 60 else 'poor')

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', '/') == '/':
                v['name'] = self.env['ir.sequence'].next_by_code('care.cafm.clean.audit') or '/'
        return super().create(vals_list)

    def action_generate_lines(self):
        for a in self:
            if not a.template_id:
                raise UserError(_('اختر قالب الفحص أولاً.'))
            a.line_ids = [(5, 0, 0)] + [(0, 0, {'name': i.name, 'weight': i.weight})
                                        for i in a.template_id.item_ids]

    def action_done(self):
        """Close the audit and raise a corrective observation per failed item."""
        for a in self:
            a.state = 'done'
            for l in a.line_ids.filtered(lambda x: x.result == 'fail'):
                obs = self.env['care.cafm.observation'].create({
                    'title': _('تدقيق نظافة: %s') % l.name,
                    'facility_id': a.facility_id.id, 'location_id': a.location_id.id,
                    'severity': 'medium', 'description': l.note or l.name,
                    'deadline': fields.Datetime.now() + timedelta(hours=4),
                })
            a.message_post(body=_('اكتمل التدقيق — الدرجة %.0f%% (%s) · %s ملاحظة تصحيح.')
                           % (a.score, dict(a._fields['rating'].selection).get(a.rating), a.fail_count))


class CleanAuditLine(models.Model):
    _name = 'care.cafm.clean.audit.line'
    _description = 'Audit Line'
    _order = 'id'

    audit_id = fields.Many2one('care.cafm.clean.audit', required=True, ondelete='cascade')
    name = fields.Char(string='البند', required=True)
    weight = fields.Integer(string='الوزن', default=1)
    result = fields.Selection([('pass', 'مطابق'), ('fail', 'مخالف'), ('na', 'لا ينطبق')],
                              string='النتيجة', default='pass')
    note = fields.Char(string='ملاحظة')


# ============ SCHEDULE (frequency compliance) ============
class CleanSchedule(models.Model):
    _name = 'care.cafm.clean.schedule'
    _description = 'Cleaning Schedule'
    _order = 'facility_id, location_id'

    location_id = fields.Many2one('care.cafm.location', string='الموقع', required=True)
    facility_id = fields.Many2one(related='location_id.facility_id', store=True)
    frequency = fields.Selection([
        ('hourly', 'كل ساعة'), ('daily', 'يومي'), ('weekly', 'أسبوعي'), ('monthly', 'شهري'),
    ], string='التردّد', default='daily', required=True)
    demand_based = fields.Boolean(string='حسب الطلب (حسّاس)',
                                  help='يُنظّف عند الحاجة (ازدحام) بدل جدول ثابت.')
    last_done = fields.Datetime(string='آخر تنظيف')
    next_due = fields.Datetime(string='الاستحقاق القادم', compute='_compute_due', store=True)
    is_due = fields.Boolean(compute='_compute_due', store=True)
    active = fields.Boolean(default=True)

    @api.depends('last_done', 'frequency')
    def _compute_due(self):
        now = fields.Datetime.now()
        for s in self:
            base = s.last_done or now
            s.next_due = base + FREQ_DELTA.get(s.frequency, timedelta(days=1))
            s.is_due = s.next_due <= now


# ============ CONSUMABLES (cleaning supplies/chemicals) ============
class CleanConsumable(models.Model):
    """Cleaning supplies & chemicals ledger per facility — deliveries and
    consumption, so a client sees what materials serve their site and stock
    never runs dry. A professional hygiene-ops signal."""
    _name = 'care.cafm.clean.consumable'
    _description = 'Cleaning Consumable'
    _inherit = ['mail.thread']
    _order = 'facility_id, name'

    name = fields.Char(string='المادة', required=True, tracking=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True, tracking=True)
    category = fields.Selection([
        ('detergent', 'منظّفات'), ('disinfectant', 'مطهّرات'), ('paper', 'ورقيات'),
        ('tools', 'أدوات ومعدّات'), ('bags', 'أكياس نفايات'), ('other', 'أخرى'),
    ], string='التصنيف', default='detergent', required=True, tracking=True)
    unit = fields.Char(string='الوحدة', default='قطعة')
    on_hand = fields.Float(string='الرصيد الحالي', tracking=True)
    min_qty = fields.Float(string='الحد الأدنى', default=0.0)
    low_stock = fields.Boolean(string='مخزون منخفض', compute='_compute_low', store=True)
    last_supply_date = fields.Date(string='آخر توريد')
    move_ids = fields.One2many('care.cafm.clean.consumable.move', 'consumable_id', string='الحركات')
    active = fields.Boolean(default=True)

    @api.depends('on_hand', 'min_qty')
    def _compute_low(self):
        for c in self:
            c.low_stock = c.min_qty > 0 and c.on_hand <= c.min_qty


class CleanConsumableMove(models.Model):
    """A supply-in or consumption-out movement for a cleaning consumable."""
    _name = 'care.cafm.clean.consumable.move'
    _description = 'Cleaning Consumable Move'
    _order = 'date desc, id desc'

    consumable_id = fields.Many2one('care.cafm.clean.consumable', string='المادة', required=True, ondelete='cascade', index=True)
    facility_id = fields.Many2one(related='consumable_id.facility_id', store=True, string='المرفق')
    move_type = fields.Selection([('in', 'توريد'), ('out', 'استهلاك')], string='النوع', default='in', required=True)
    quantity = fields.Float(string='الكمية', required=True)
    date = fields.Date(string='التاريخ', default=fields.Date.context_today, required=True)
    done_by = fields.Many2one('hr.employee', string='المنفّذ')
    note = fields.Char(string='ملاحظة')

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for m in moves:
            c = m.consumable_id
            c.on_hand += m.quantity if m.move_type == 'in' else -m.quantity
            if m.move_type == 'in':
                c.last_supply_date = m.date
        return moves


# ============ CLEANING ROUND (scan in/out + before/after) ============
class CleanRound(models.Model):
    _name = 'care.cafm.clean.round'
    _description = 'Cleaning Round'
    _order = 'id desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    worker_id = fields.Many2one('hr.employee', string='العامل')
    location_id = fields.Many2one('care.cafm.location', string='الموقع', required=True)
    facility_id = fields.Many2one(related='location_id.facility_id', store=True)
    scan_in_time = fields.Datetime(string='دخول (مسح)', readonly=True, copy=False)
    scan_out_time = fields.Datetime(string='خروج (مسح)', readonly=True, copy=False)
    duration_minutes = fields.Float(compute='_compute_dur', store=True)
    before_note = fields.Char(string='قبل')
    after_note = fields.Char(string='بعد')
    state = fields.Selection([('open', 'جارية'), ('done', 'منتهية')], default='open')

    @api.depends('scan_in_time', 'scan_out_time')
    def _compute_dur(self):
        for r in self:
            r.duration_minutes = ((r.scan_out_time - r.scan_in_time).total_seconds() / 60.0
                                  if r.scan_in_time and r.scan_out_time else 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', '/') == '/':
                v['name'] = self.env['ir.sequence'].next_by_code('care.cafm.clean.round') or '/'
        return super().create(vals_list)

    def action_scan_in(self):
        for r in self:
            r.scan_in_time = fields.Datetime.now()
            self.env['care.cafm.scan'].create({
                'employee_id': r.worker_id.id, 'location_id': r.location_id.id, 'scan_type': 'clean_in'})

    def action_scan_out(self):
        for r in self:
            r.write({'scan_out_time': fields.Datetime.now(), 'state': 'done'})
            self.env['care.cafm.scan'].create({
                'employee_id': r.worker_id.id, 'location_id': r.location_id.id, 'scan_type': 'clean_out'})
            sched = self.env['care.cafm.clean.schedule'].search([('location_id', '=', r.location_id.id)], limit=1)
            if sched:
                sched.last_done = fields.Datetime.now()
