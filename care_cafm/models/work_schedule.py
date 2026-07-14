# -*- coding: utf-8 -*-
"""جداول الأعمال — recurring, assigned, interval-based duties.

A schedule = "clean this bathroom every 60 min" or "patrol the gates every 30
min" within a daily window. A cron materialises one *occurrence* per due slot,
notifies the assigned worker, and tracks whether each visit was done on time,
late, or missed — with presence proof + photo evidence per occurrence."""
from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models, _

TZ = 'Asia/Kuwait'


class CafmSchedule(models.Model):
    _name = 'care.cafm.schedule'
    _description = 'جدول عمل متكرر'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='الجدول', required=True, tracking=True, translate=True)
    code = fields.Char(string='الرمز', copy=False, readonly=True, default=lambda s: _('جديد'))
    active = fields.Boolean(default=True)
    service_id = fields.Many2one('care.cafm.service', string='الخدمة', required=True, tracking=True)
    service_type = fields.Selection(related='service_id.service_type', store=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True, tracking=True)
    location_id = fields.Many2one('care.cafm.location', string='الموقع (QR)', tracking=True,
                                  domain="[('facility_id','=',facility_id)]",
                                  help='المكان الذي يجب زيارته ومسح رمزه لإثبات الحضور.')
    employee_id = fields.Many2one('hr.employee', string='المُسنَد إليه', required=True, tracking=True)

    every_minutes = fields.Integer(string='التكرار كل (دقيقة)', default=60, required=True, tracking=True,
                                   help='مثال: 60 = كل ساعة، 30 = كل نصف ساعة.')
    window_start = fields.Float(string='بداية النافذة', default=7.0, help='بصيغة 24 ساعة')
    window_end = fields.Float(string='نهاية النافذة', default=19.0)
    days = fields.Char(string='الأيام', default='السبت–الخميس')
    grace_minutes = fields.Integer(string='مهلة السماح (دقيقة)', default=10,
                                   help='بعدها تُعتبر الزيارة متأخرة.')

    require_presence = fields.Boolean(string='إثبات حضور (QR)', default=True)
    require_photo = fields.Boolean(string='صورة إثبات', default=True)
    require_video = fields.Boolean(string='فيديو إثبات', default=False)
    instructions = fields.Text(string='المطلوب تنفيذه')
    color = fields.Integer()
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    occurrence_ids = fields.One2many('care.cafm.schedule.occurrence', 'schedule_id', string='التكرارات')
    occ_total = fields.Integer(compute='_compute_stats', string='الكل')
    occ_done = fields.Integer(compute='_compute_stats', string='منجزة')
    occ_late = fields.Integer(compute='_compute_stats', string='متأخرة')
    occ_missed = fields.Integer(compute='_compute_stats', string='فائتة')
    compliance = fields.Float(compute='_compute_stats', string='الالتزام %')

    @api.depends('occurrence_ids.state')
    def _compute_stats(self):
        for s in self:
            occ = s.occurrence_ids
            s.occ_total = len(occ)
            s.occ_done = len(occ.filtered(lambda o: o.state == 'done'))
            s.occ_late = len(occ.filtered(lambda o: o.state == 'late'))
            s.occ_missed = len(occ.filtered(lambda o: o.state == 'missed'))
            closed = s.occ_done + s.occ_late + s.occ_missed
            s.compliance = round(100.0 * s.occ_done / closed, 1) if closed else 100.0

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('code', _('جديد')) in (_('جديد'), 'New', '/', False):
                v['code'] = self.env['ir.sequence'].next_by_code('care.cafm.schedule') or '/'
        return super().create(vals_list)

    # ---- slot generation ----
    def _slots_for_day(self, day):
        """Return the list of due datetimes (UTC, naive) for a given local date."""
        self.ensure_one()
        tz = pytz.timezone(self.env.user.tz or TZ)
        out = []
        start = self.window_start or 0.0
        end = self.window_end or 24.0
        step = max(1, self.every_minutes or 60)
        mins = int(start * 60)
        end_mins = int(end * 60)
        while mins <= end_mins:
            hh, mm = divmod(mins, 60)
            if hh < 24:
                local = tz.localize(datetime.combine(day, time(hh, mm)))
                out.append(local.astimezone(pytz.utc).replace(tzinfo=None))
            mins += step
        return out

    def action_generate_today(self):
        for s in self:
            s._generate_upto(fields.Datetime.now() + timedelta(minutes=s.every_minutes))
        return True

    def _generate_upto(self, until):
        """Materialise occurrences for today's slots up to `until` (UTC)."""
        Occ = self.env['care.cafm.schedule.occurrence'].sudo()
        for s in self:
            if not s.active:
                continue
            today = fields.Date.context_today(s)
            existing = set(Occ.search([('schedule_id', '=', s.id)]).mapped('planned_time'))
            for slot in s._slots_for_day(today):
                if slot <= until and slot not in existing:
                    Occ.create({
                        'schedule_id': s.id, 'planned_time': slot,
                        'employee_id': s.employee_id.id,
                    })

    @api.model
    def _cron_run(self):
        """Generate due occurrences, notify workers, and flag late/missed."""
        now = fields.Datetime.now()
        schedules = self.search([('active', '=', True)])
        schedules._generate_upto(now + timedelta(minutes=5))
        Occ = self.env['care.cafm.schedule.occurrence'].sudo()
        pend = Occ.search([('state', '=', 'pending'), ('schedule_id.active', '=', True)])
        for o in pend:
            sched = o.schedule_id
            # notify at due time
            if o.planned_time and o.planned_time <= now and not o.notified:
                if o.employee_id.user_id and 'care.cafm.notification' in self.env:
                    self.env['care.cafm.notification'].sudo().push(
                        o.employee_id.user_id, '⏰ مهمة مجدولة الآن',
                        '%s — %s' % (sched.name, sched.location_id.name or sched.facility_id.name),
                        ntype='task', action_url='/schedule/occurrence/%s' % o.id)
                o.notified = True
            # late / missed
            if o.planned_time:
                grace = timedelta(minutes=sched.grace_minutes or 0)
                if now > o.planned_time + timedelta(minutes=(sched.every_minutes or 60)):
                    o.state = 'missed'
                elif now > o.planned_time + grace:
                    o.state = 'late'


class CafmScheduleOccurrence(models.Model):
    _name = 'care.cafm.schedule.occurrence'
    _description = 'تكرار جدول عمل'
    _order = 'planned_time desc'

    name = fields.Char(compute='_compute_name', store=True)
    schedule_id = fields.Many2one('care.cafm.schedule', string='الجدول', required=True, ondelete='cascade', index=True)
    service_id = fields.Many2one(related='schedule_id.service_id', store=True, string='الخدمة')
    service_type = fields.Selection(related='schedule_id.service_type', store=True)
    facility_id = fields.Many2one(related='schedule_id.facility_id', store=True, string='المرفق')
    location_id = fields.Many2one(related='schedule_id.location_id', store=True, string='الموقع')
    employee_id = fields.Many2one('hr.employee', string='المُسنَد إليه', index=True)

    planned_time = fields.Datetime(string='الوقت المقرّر', required=True, index=True)
    actual_time = fields.Datetime(string='وقت التنفيذ', readonly=True)
    state = fields.Selection([
        ('pending', 'قيد الانتظار'), ('done', 'منجزة في الوقت'),
        ('late', 'متأخرة'), ('missed', 'فائتة'),
    ], string='الحالة', default='pending', index=True, tracking=True)
    presence_verified = fields.Boolean(string='أُثبت الحضور', readonly=True)
    response_delay_minutes = fields.Integer(string='تأخّر الاستجابة (دقيقة)', compute='_compute_delay', store=True)
    result_description = fields.Text(string='وصف النتيجة')
    proof_photo = fields.Image(string='صورة الإثبات', max_width=1600, max_height=1600)
    proof_photo2 = fields.Image(string='صورة إثبات إضافية', max_width=1600, max_height=1600)
    notified = fields.Boolean(default=False)
    company_id = fields.Many2one(related='schedule_id.company_id', store=True)

    @api.depends('schedule_id.code', 'planned_time')
    def _compute_name(self):
        for o in self:
            o.name = '%s @ %s' % (o.schedule_id.code or '', o.planned_time or '')

    @api.depends('actual_time', 'planned_time')
    def _compute_delay(self):
        for o in self:
            if o.actual_time and o.planned_time:
                o.response_delay_minutes = int((o.actual_time - o.planned_time).total_seconds() / 60)
            else:
                o.response_delay_minutes = 0

    def action_complete(self, presence=True, result=None):
        """Mark this occurrence executed (called from portal/app)."""
        self.ensure_one()
        now = fields.Datetime.now()
        grace = self.schedule_id.grace_minutes or 0
        self.write({
            'actual_time': now,
            'presence_verified': bool(presence),
            'result_description': result or self.result_description,
            'state': 'late' if (self.planned_time and now > self.planned_time + timedelta(minutes=grace)) else 'done',
        })
        return True
