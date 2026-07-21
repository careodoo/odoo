# -*- coding: utf-8 -*-
"""جداول الأعمال — recurring, assigned, interval-based duties.

A schedule = "clean this bathroom every 60 min" or "patrol the gates every 30
min" within a daily window. A cron materialises one *occurrence* per due slot,
notifies the assigned worker, and tracks whether each visit was done on time,
late, or missed — with presence proof + photo evidence per occurrence."""
from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

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
    employee_id = fields.Many2one('hr.employee', string='المُسنَد إليه', tracking=True)

    # People think in "every 2 hours" or "every 3 months", not in 120 or
    # 129600 minutes. The unit pair is what is edited; every_minutes stays as
    # the computed engine value so the generator and every caller keep working.
    interval_value = fields.Integer(string='التكرار كل', default=1, required=True, tracking=True)
    interval_unit = fields.Selection([
        ('minute', 'دقيقة'), ('hour', 'ساعة'), ('day', 'يوم'), ('month', 'شهر'),
    ], string='الوحدة', default='hour', required=True, tracking=True)
    every_minutes = fields.Integer(string='التكرار بالدقائق', compute='_compute_every',
                                   store=True, readonly=True,
                                   help='القيمة المحسوبة التي يعمل بها المولّد.')

    # Assigning to a team rather than a person is the normal case on a site
    # where whoever is on shift takes the round.
    team_id = fields.Many2one('care.cafm.team', string='الفريق المُسنَد',
                              tracking=True, domain="[('facility_id','=',facility_id)]")

    remind_before = fields.Integer(string='التنبيه قبل الموعد بـ', default=15, tracking=True)
    remind_unit = fields.Selection([
        ('minute', 'دقيقة'), ('hour', 'ساعة'), ('day', 'يوم'),
    ], string='وحدة التنبيه', default='minute', required=True)
    remind_minutes = fields.Integer(compute='_compute_every', store=True)
    # A shift preset drives the window (and therefore the auto-stop time): pick
    # "الصباحية" and generation stops at the end of the morning shift.
    shift = fields.Selection([
        ('custom', 'مخصّص'),
        ('morning', 'الوردية الصباحية (٦ص–٢م)'),
        ('evening', 'الوردية المسائية (٢م–١٠م)'),
        ('night', 'الوردية الليلية (١٠م–٦ص)'),
    ], string='الوردية', default='custom', tracking=True,
        help='اختيار وردية يضبط نافذة العمل ووقت الإيقاف تلقائياً على نهايتها.')
    stop_mode = fields.Selection([
        ('window', 'الإيقاف عند نهاية النافذة/الوردية'),
        ('none', 'بلا إيقاف تلقائي (طوال اليوم)'),
    ], string='نمط الإيقاف', default='window', tracking=True,
        help='«عند نهاية النافذة» يوقف توليد المهام بعد نهاية الوردية؛ '
             '«بلا إيقاف» يولّدها طوال اليوم.')
    window_start = fields.Float(string='بداية النافذة', default=7.0, help='بصيغة 24 ساعة')
    window_end = fields.Float(string='نهاية النافذة (وقت الإيقاف)', default=19.0)
    days = fields.Char(string='الأيام', default='السبت–الخميس')
    grace_minutes = fields.Integer(string='مهلة السماح (دقيقة)', default=10,
                                   help='بعدها تُعتبر الزيارة متأخرة.')
    # ad-hoc exceptions: skip specific days (holidays) or specific hours on a range
    exception_ids = fields.One2many('care.cafm.schedule.exception', 'schedule_id',
                                    string='الاستثناءات',
                                    help='فترات لا يُولَّد فيها عمل — إجازات أو ساعات إيقاف محددة.')

    SHIFT_WINDOWS = {'morning': (6.0, 14.0), 'evening': (14.0, 22.0), 'night': (22.0, 24.0)}

    @api.onchange('shift')
    def _onchange_shift(self):
        w = self.SHIFT_WINDOWS.get(self.shift)
        if w:
            self.window_start, self.window_end = w

    # temporary pause (paused/pause_until) vs permanent stop (active=False)
    paused = fields.Boolean(string='موقوف مؤقتاً', default=False, tracking=True)
    pause_until = fields.Date(string='إيقاف حتى', tracking=True,
                              help='يُستأنف تلقائياً بعد هذا التاريخ. اتركه فارغاً لإيقاف مؤقت مفتوح.')
    pause_reason = fields.Char(string='سبب الإيقاف')

    require_presence = fields.Boolean(string='إثبات حضور (QR)', default=True)
    require_photo = fields.Boolean(string='صورة إثبات', default=True)
    require_video = fields.Boolean(string='فيديو إثبات', default=False)
    instructions = fields.Text(string='المطلوب تنفيذه')
    color = fields.Integer()
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    next_run = fields.Datetime(string='الموعد القادم', compute='_compute_next', store=True,
                               index=True)
    minutes_to_next = fields.Integer(string='المتبقّي (دقيقة)', compute='_compute_next')
    countdown = fields.Char(string='العدّ التنازلي', compute='_compute_next',
                            help='الوقت المتبقّي للعمل القادم، بصيغة يقرأها الإنسان.')
    is_due_now = fields.Boolean(string='حان موعده', compute='_compute_next')

    occurrence_ids = fields.One2many('care.cafm.schedule.occurrence', 'schedule_id', string='التكرارات')
    occ_total = fields.Integer(compute='_compute_stats', string='الكل')
    occ_done = fields.Integer(compute='_compute_stats', string='منجزة')
    occ_late = fields.Integer(compute='_compute_stats', string='متأخرة')
    occ_missed = fields.Integer(compute='_compute_stats', string='فائتة')
    compliance = fields.Float(compute='_compute_stats', string='الالتزام %')

    UNIT_MIN = {'minute': 1, 'hour': 60, 'day': 1440, 'month': 43200}

    @api.depends('interval_value', 'interval_unit', 'remind_before', 'remind_unit')
    def _compute_every(self):
        for s in self:
            s.every_minutes = max(1, (s.interval_value or 1) * self.UNIT_MIN.get(s.interval_unit, 60))
            s.remind_minutes = max(0, (s.remind_before or 0) * self.UNIT_MIN.get(s.remind_unit, 1))

    @api.depends('occurrence_ids.planned_time', 'occurrence_ids.state',
                 'every_minutes', 'paused', 'pause_until', 'active')
    def _compute_next(self):
        now = fields.Datetime.now()
        for s in self:
            nxt = False
            if s.active and not s._paused_now():
                pending = s.occurrence_ids.filtered(
                    lambda o: o.state in ('pending', 'due') and o.planned_time
                    and o.planned_time >= now).sorted('planned_time')
                if pending:
                    nxt = pending[0].planned_time
                else:
                    # nothing materialised yet — say when the next slot lands
                    slots = [x for x in s._slots_for_day(fields.Date.context_today(s)) if x > now]
                    if not slots:
                        tomorrow = fields.Date.context_today(s) + timedelta(days=1)
                        slots = s._slots_for_day(tomorrow)
                    nxt = slots[0] if slots else False
            s.next_run = nxt
            if not nxt:
                s.minutes_to_next, s.countdown, s.is_due_now = 0, '—', False
                continue
            mins = int((nxt - now).total_seconds() // 60)
            s.minutes_to_next = mins
            s.is_due_now = mins <= 0
            s.countdown = s._humanise(mins)

    @api.model
    def _humanise(self, mins):
        """A countdown someone can read at a glance: overdue, minutes, hours,
        or days — never '2143 minutes'."""
        if mins <= 0:
            return _('حان الآن')
        if mins < 60:
            return _('%s دقيقة') % mins
        if mins < 1440:
            h, m = divmod(mins, 60)
            return _('%sس %sد') % (h, m) if m else _('%s ساعة') % h
        d, rem = divmod(mins, 1440)
        h = rem // 60
        return _('%s يوم %s س') % (d, h) if h else _('%s يوم') % d

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
        # a whole-day exception (holiday / stop-day) skips the day entirely
        if any(e._blocks_day(day) for e in self.exception_ids):
            return out
        start = self.window_start or 0.0
        # stop_mode='none' → run all day; else stop at the window/shift end
        end = 24.0 if self.stop_mode == 'none' else (self.window_end or 24.0)
        step = max(1, self.every_minutes or 60)
        mins = int(start * 60)
        end_mins = int(end * 60)
        while mins <= end_mins:
            hh, mm = divmod(mins, 60)
            if hh < 24:
                hour = mins / 60.0
                # skip any hour that falls inside an hours-exception for this day
                if not any(e._blocks_hour(day, hour) for e in self.exception_ids):
                    local = tz.localize(datetime.combine(day, time(hh, mm)))
                    out.append(local.astimezone(pytz.utc).replace(tzinfo=None))
            mins += step
        return out

    def _paused_now(self):
        """True while a temporary pause is in effect; auto-resumes once the
        pause_until date has passed."""
        self.ensure_one()
        if not self.paused:
            return False
        if self.pause_until and fields.Date.context_today(self) > self.pause_until:
            self.paused = False
            self.pause_until = False
            self.message_post(body=_('استُؤنف الجدول تلقائياً بانتهاء مدة الإيقاف.'))
            return False
        return True

    def action_pause(self):
        """Temporarily pause: stop generating/notifying until resumed or until
        pause_until passes."""
        self.write({'paused': True})
        return True

    def action_resume(self):
        self.write({'paused': False, 'pause_until': False})
        return True

    def action_stop_permanent(self):
        """Permanently stop the schedule (archive). Reactivate to bring back."""
        self.write({'active': False, 'paused': False})
        return True

    def action_reactivate(self):
        self.write({'active': True})
        return True

    def action_generate_today(self):
        for s in self:
            s._generate_upto(fields.Datetime.now() + timedelta(minutes=s.every_minutes))
        return True

    def _generate_upto(self, until):
        """Materialise occurrences for today's slots up to `until` (UTC)."""
        Occ = self.env['care.cafm.schedule.occurrence'].sudo()
        for s in self:
            if not s.active or s._paused_now():
                continue
            today = fields.Date.context_today(s)
            existing = set(Occ.search([('schedule_id', '=', s.id)]).mapped('planned_time'))
            for slot in s._slots_for_day(today):
                if slot <= until and slot not in existing:
                    emp = s.employee_id
                    if not emp and s.team_id:
                        # whoever is on the team takes it; the first member is a
                        # placeholder the supervisor can reassign
                        emp = s.team_id.member_ids[:1]
                    Occ.create({
                        'schedule_id': s.id, 'planned_time': slot,
                        'employee_id': emp.id if emp else False,
                    })

    def _send_reminders(self, now):
        """Warn before the slot, not when it is already late. A reminder that
        arrives at the due minute is just a second way of saying 'overdue'."""
        Occ = self.env['care.cafm.schedule.occurrence'].sudo()
        if 'care.cafm.notification' not in self.env:
            return
        for s in self.filtered(lambda x: x.remind_minutes > 0):
            window_end = now + timedelta(minutes=s.remind_minutes)
            due = Occ.search([('schedule_id', '=', s.id), ('state', '=', 'pending'),
                              ('planned_time', '>', now), ('planned_time', '<=', window_end),
                              ('reminded', '=', False)])
            if not due:
                continue
            people = s.employee_id or s.team_id.member_ids
            users = people.mapped('user_id')
            if not users:
                continue
            for o in due:
                try:
                    self.env['care.cafm.notification'].sudo().push(
                        users, _('⏰ عمل مجدول بعد %s') % s._humanise(s.remind_minutes),
                        '%s — %s' % (s.name, s.location_id.name or s.facility_id.name or ''),
                        ntype='task')
                except Exception:
                    pass
            due.write({'reminded': True})

    @api.model
    def _cron_run(self):
        """Generate due occurrences, notify workers, and flag late/missed."""
        now = fields.Datetime.now()
        schedules = self.search([('active', '=', True)]).filtered(lambda s: not s._paused_now())
        schedules._send_reminders(now)
        schedules._generate_upto(now + timedelta(minutes=5))
        Occ = self.env['care.cafm.schedule.occurrence'].sudo()
        pend = Occ.search([('state', '=', 'pending'), ('schedule_id.active', '=', True)])
        for o in pend:
            sched = o.schedule_id
            if sched._paused_now():
                continue
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
    reminded = fields.Boolean(string='أُرسل التنبيه', default=False, copy=False)
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


class WorkScheduleException(models.Model):
    """A window during which a schedule generates no work — a public holiday, a
    site closure, or just 'no rounds between 1pm and 3pm on these dates'."""
    _name = 'care.cafm.schedule.exception'
    _description = 'استثناء جدول العمل'
    _order = 'date_from desc, id desc'

    schedule_id = fields.Many2one('care.cafm.schedule', string='الجدول',
                                  required=True, ondelete='cascade', index=True)
    name = fields.Char(string='السبب', required=True)
    date_from = fields.Date(string='من تاريخ', required=True,
                            default=fields.Date.context_today)
    date_to = fields.Date(string='إلى تاريخ', required=True,
                          default=fields.Date.context_today,
                          help='شامل — الاستثناء يغطّي هذا اليوم أيضاً.')
    whole_day = fields.Boolean(string='يوم كامل', default=True,
                               help='مفعّل: توقّف طوال اليوم. معطّل: توقّف ساعات محددة فقط.')
    hour_from = fields.Float(string='من الساعة', default=0.0, help='بصيغة 24 ساعة')
    hour_to = fields.Float(string='إلى الساعة', default=24.0)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for e in self:
            if e.date_to < e.date_from:
                raise ValidationError(_('«إلى تاريخ» يجب أن يكون بعد «من تاريخ».'))

    def _in_range(self, day):
        self.ensure_one()
        return self.date_from <= day <= self.date_to

    def _blocks_day(self, day):
        """True if this exception cancels the WHOLE given day."""
        return self.whole_day and self._in_range(day)

    def _blocks_hour(self, day, hour):
        """True if this exception cancels a specific hour on the given day."""
        if self.whole_day or not self._in_range(day):
            return False
        return (self.hour_from or 0.0) <= hour < (self.hour_to or 24.0)
