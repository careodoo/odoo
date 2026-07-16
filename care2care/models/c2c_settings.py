# -*- coding: utf-8 -*-
"""CARE 2 CARE booking availability settings + slot computation.
Available slots = working hours − already-booked slots (per-slot team capacity),
respecting working days, lead time and booking horizon."""
from datetime import datetime, timedelta
from odoo import api, fields, models


class C2CSettings(models.Model):
    _name = 'c2c.settings'
    _description = 'CARE 2 CARE Booking Settings'

    name = fields.Char(default='إعدادات الحجز', readonly=True)
    work_start = fields.Float(string='بداية الدوام', default=8.0, help='الساعة (0–24).')
    work_end = fields.Float(string='نهاية الدوام', default=22.0)
    slot_minutes = fields.Integer(string='مدة الموعد (دقيقة)', default=60)
    capacity_per_slot = fields.Integer(string='السعة لكل موعد', default=3,
                                       help='أقصى حجوزات متزامنة في الموعد الواحد (يُقيَّد أيضًا بعدد الفريق المتاح).')
    use_team_capacity = fields.Boolean(string='قيّد السعة بعدد الفريق', default=True)
    lead_hours = fields.Integer(string='أقل مهلة للحجز (ساعة)', default=3)
    horizon_days = fields.Integer(string='مدى الحجز المتاح (يوم)', default=30)
    day_mon = fields.Boolean(string='الإثنين', default=True)
    day_tue = fields.Boolean(string='الثلاثاء', default=True)
    day_wed = fields.Boolean(string='الأربعاء', default=True)
    day_thu = fields.Boolean(string='الخميس', default=True)
    day_fri = fields.Boolean(string='الجمعة', default=False)
    day_sat = fields.Boolean(string='السبت', default=True)
    day_sun = fields.Boolean(string='الأحد', default=True)
    order_notify_user_ids = fields.Many2many(
        'res.users', 'c2c_settings_order_notify_rel', 'settings_id', 'user_id',
        string='المنبَّهون بطلبات المتجر',
        help='المستخدمون الذين يصلهم تنبيه عند وصول طلب متجر جديد أو طلب إلغاء. '
             'إذا تُرك فارغًا لا يُرسَل أي تنبيه.')
    booking_notify_user_ids = fields.Many2many(
        'res.users', 'c2c_settings_booking_notify_rel', 'settings_id', 'user_id',
        string='المنبَّهون بالحجوزات',
        help='المستخدمون الذين يصلهم تنبيه عند وصول حجز خدمة جديد أو إلغاء حجز. '
             'إذا تُرك فارغًا لا يُرسَل أي تنبيه.')
    contract_notify_user_ids = fields.Many2many(
        'res.users', 'c2c_settings_contract_notify_rel', 'settings_id', 'user_id',
        string='المنبَّهون بطلبات التعاقد',
        help='المستخدمون الذين يصلهم تنبيه عند وصول طلب تعاقد / عرض سعر جديد. '
             'إذا تُرك فارغًا لا يُرسَل أي تنبيه.')

    @api.model
    def get_settings(self):
        rec = self.search([], limit=1)
        if not rec:
            rec = self.create({})
        return rec

    def _working_day(self, weekday):
        # python weekday(): Mon=0 .. Sun=6
        return [self.day_mon, self.day_tue, self.day_wed, self.day_thu,
                self.day_fri, self.day_sat, self.day_sun][weekday]

    @api.model
    def compute_slots(self, service, date_str):
        """Return [{'time': 'HH:MM', 'available': bool, 'remaining': int}] for a
        service on a given YYYY-MM-DD date."""
        cfg = self.get_settings()
        try:
            day = fields.Date.from_string(date_str)
        except Exception:
            return []
        if not cfg._working_day(day.weekday()):
            return []
        now = fields.Datetime.now()
        earliest = now + timedelta(hours=cfg.lead_hours)
        step = max(15, cfg.slot_minutes)
        # team capacity for this service's category
        cap = cfg.capacity_per_slot
        if cfg.use_team_capacity and 'c2c.provider' in self.env and service:
            provs = self.env['c2c.provider'].sudo().search([('available', '=', True)])
            qualified = provs.filtered(lambda p: not p.category_ids or service.category_id in p.category_ids)
            if qualified:
                cap = min(cap, len(qualified)) if cap else len(qualified)
        cap = max(1, cap or 1)
        Booking = self.env['c2c.booking'].sudo()
        slots = []
        start_min = int(cfg.work_start * 60)
        end_min = int(cfg.work_end * 60)
        t = start_min
        while t + cfg.slot_minutes <= end_min + 1:
            hh, mm = divmod(t, 60)
            slot_dt = datetime(day.year, day.month, day.day, hh, mm)
            if slot_dt >= earliest:
                # bookings overlapping this slot (same start), excluding cancelled
                cnt = Booking.search_count([
                    ('service_id.category_id', '=', service.category_id.id) if service else ('id', '!=', 0),
                    ('visit_datetime', '>=', fields.Datetime.to_string(slot_dt)),
                    ('visit_datetime', '<', fields.Datetime.to_string(slot_dt + timedelta(minutes=cfg.slot_minutes))),
                    ('state', '!=', 'cancelled'),
                ])
                remaining = max(0, cap - cnt)
                slots.append({'time': '%02d:%02d' % (hh, mm), 'available': remaining > 0, 'remaining': remaining})
            t += step
        return slots
