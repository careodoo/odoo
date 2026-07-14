# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import fields, models, api, _


# ============ PEST CONTROL ============
class PestStation(models.Model):
    _name = 'care.cafm.pest.station'
    _description = 'Pest Bait/Trap Station'
    _order = 'facility_id, name'

    name = fields.Char(string='المحطة', required=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True)
    location_id = fields.Many2one('care.cafm.location', string='الموقع')
    station_type = fields.Selection([
        ('bait', 'طعم'), ('trap', 'فخّ'), ('monitor', 'مراقبة'),
    ], string='النوع', default='bait')
    last_check = fields.Date(string='آخر فحص')
    activity_level = fields.Selection([
        ('none', 'لا نشاط'), ('low', 'منخفض'), ('high', 'مرتفع'),
    ], string='مستوى النشاط', default='none')
    active = fields.Boolean(default=True)


class PestVisit(models.Model):
    _name = 'care.cafm.pest.visit'
    _description = 'Pest Control Visit'
    _order = 'date desc, id desc'

    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    technician_id = fields.Many2one('hr.employee', string='الفنّي')
    findings = fields.Text(string='الملاحظات')
    action_taken = fields.Text(string='الإجراء')
    product = fields.Char(string='المبيد المستخدم')


# ============ WASTE ============
class WastePickup(models.Model):
    _name = 'care.cafm.waste.pickup'
    _description = 'Waste Pickup'
    _order = 'date desc, id desc'

    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    waste_type = fields.Selection([
        ('general', 'عام'), ('recyclable', 'قابل للتدوير'), ('hazardous', 'خطِر'),
        ('medical', 'طبي'), ('organic', 'عضوي'),
    ], string='النوع', default='general', required=True)
    weight_kg = fields.Float(string='الوزن (كجم)')
    recycled = fields.Boolean(string='أُعيد تدويره')
    note = fields.Char()


# ============ POOL ============
class PoolReading(models.Model):
    _name = 'care.cafm.pool.reading'
    _description = 'Pool Water Reading'
    _order = 'reading_time desc, id desc'

    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True)
    location_id = fields.Many2one('care.cafm.location', string='المسبح')
    reading_time = fields.Datetime(string='الوقت', default=fields.Datetime.now, required=True)
    chlorine = fields.Float(string='الكلور (ppm)')
    ph = fields.Float(string='الأس الهيدروجيني (pH)')
    temperature = fields.Float(string='الحرارة °م')
    status = fields.Selection([
        ('ok', 'ضمن الآمن'), ('attention', 'يحتاج ضبط'),
    ], compute='_compute_status', store=True)

    @api.depends('chlorine', 'ph')
    def _compute_status(self):
        for r in self:
            cl_ok = 1.0 <= (r.chlorine or 0) <= 3.0
            ph_ok = 7.2 <= (r.ph or 0) <= 7.8
            r.status = 'ok' if (cl_ok and ph_ok) else 'attention'


# ============ WATER TANK (Kuwait regulated) ============
class WaterTank(models.Model):
    _name = 'care.cafm.watertank'
    _description = 'Water Tank Cleaning'
    _inherit = ['mail.thread']
    _order = 'facility_id, name'

    name = fields.Char(string='الخزان', required=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True)
    location_id = fields.Many2one('care.cafm.location', string='الموقع')
    capacity_m3 = fields.Float(string='السعة (م³)')
    frequency_months = fields.Integer(string='الدورية (شهور)', default=6)
    last_cleaned = fields.Date(string='آخر تنظيف', tracking=True)
    next_due = fields.Date(compute='_compute_due', store=True)
    is_due = fields.Boolean(compute='_compute_due', store=True)
    certificate = fields.Boolean(string='شهادة تنظيف صادرة')
    lab_result = fields.Char(string='نتيجة تحليل المياه')

    @api.depends('last_cleaned', 'frequency_months')
    def _compute_due(self):
        today = fields.Date.today()
        for t in self:
            if t.last_cleaned:
                t.next_due = t.last_cleaned + timedelta(days=30 * (t.frequency_months or 6))
            else:
                t.next_due = today
            t.is_due = t.next_due <= today

    def action_clean(self):
        for t in self:
            t.write({'last_cleaned': fields.Date.today(), 'certificate': True})
            t.message_post(body=_('🚰 تم تنظيف الخزان وإصدار الشهادة.'))
