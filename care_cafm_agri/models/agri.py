# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import fields, models, api, _

FREQ = {'daily': timedelta(days=1), 'alt': timedelta(days=2),
        'weekly': timedelta(weeks=1), 'biweekly': timedelta(weeks=2)}


class AgriSpecies(models.Model):
    """Species / plant-type catalogue with agronomic care requirements.
    Central reference so every tree of a species inherits its pruning,
    watering and fertilizing needs — the backbone of real landscaping ops."""
    _name = 'care.cafm.agri.species'
    _description = 'Plant Species'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='النوع', required=True, tracking=True)
    scientific_name = fields.Char(string='الاسم العلمي', tracking=True)
    category = fields.Selection([
        ('tree', 'شجرة'), ('palm', 'نخيل'), ('shrub', 'شجيرة'),
        ('flower', 'زهور'), ('grass', 'مسطحات خضراء'), ('cactus', 'صبّار/عصاري'),
        ('groundcover', 'غطاء أرضي'), ('other', 'أخرى'),
    ], string='التصنيف', default='tree', required=True, tracking=True)
    image = fields.Image(string='صورة', max_width=1024, max_height=1024)
    # Care requirements
    water_need = fields.Selection([
        ('low', 'قليل'), ('medium', 'متوسط'), ('high', 'كثير'),
    ], string='احتياج الماء', default='medium', tracking=True)
    sun_exposure = fields.Selection([
        ('full', 'شمس كاملة'), ('partial', 'ظل جزئي'), ('shade', 'ظل'),
    ], string='التعرّض للشمس', default='full', tracking=True)
    prune_interval_days = fields.Integer(string='دورة التقليم (يوم)', default=180, tracking=True,
                                         help='كل كم يوم يُنصح بتقليم هذا النوع.')
    fertilize_interval_days = fields.Integer(string='دورة التسميد (يوم)', default=90, tracking=True)
    heat_tolerant = fields.Boolean(string='يتحمّل حرارة الكويت 🇰🇼', tracking=True,
                                   help='مناسب لمناخ الخليج الحار — يقلّل الفقد الموسمي.')
    salt_tolerant = fields.Boolean(string='يتحمّل الملوحة', tracking=True)
    care_guide = fields.Text(string='دليل العناية')
    plant_ids = fields.One2many('care.cafm.agri.plant', 'species_id', string='الأشجار/النباتات')
    plant_count = fields.Integer(string='العدد', compute='_compute_plant_count')
    active = fields.Boolean(default=True)

    @api.depends('plant_ids')
    def _compute_plant_count(self):
        for s in self:
            s.plant_count = len(s.plant_ids)

    def action_view_plants(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('أشجار %s') % self.name,
            'res_model': 'care.cafm.agri.plant', 'view_mode': 'tree,form,kanban',
            'domain': [('species_id', '=', self.id)],
            'context': {'default_species_id': self.id},
        }


class AgriZone(models.Model):
    """Irrigation zone with smart (weather/moisture) scheduling — Kuwait heat."""
    _name = 'care.cafm.agri.zone'
    _description = 'Irrigation Zone'
    _inherit = ['mail.thread']
    _order = 'facility_id, name'

    name = fields.Char(string='المنطقة', required=True, tracking=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True, tracking=True)
    location_id = fields.Many2one('care.cafm.location', string='الموقع', tracking=True)
    method = fields.Selection([
        ('drip', 'تنقيط'), ('sprinkler', 'رشّاشات'), ('bubbler', 'فقاعات'), ('manual', 'يدوي'),
    ], string='طريقة الريّ', default='drip', tracking=True)
    frequency = fields.Selection([
        ('daily', 'يومي'), ('alt', 'يوم بعد يوم'), ('weekly', 'أسبوعي'), ('biweekly', 'كل أسبوعين'),
    ], string='التردّد', default='daily', required=True, tracking=True)
    # Smart irrigation schedule
    start_time = fields.Float(string='وقت البدء', default=5.0, help='الساعة (0–24) لبدء الريّ — يُفضّل الفجر/الليل صيفًا.')
    duration_min = fields.Integer(string='مدة الريّ (دقيقة)', default=20, tracking=True)
    flow_lpm = fields.Float(string='التدفّق (لتر/دقيقة)')
    weather_based = fields.Boolean(string='ذكي حسب الطقس 🇰🇼', tracking=True,
                                   help='يُعدّل الريّ حسب الحرارة/الرطوبة لتوفير المياه.')
    valve_state = fields.Selection([
        ('closed', 'مغلق'), ('open', 'مفتوح'), ('fault', 'عطل'),
    ], string='حالة المحبس', default='closed', tracking=True)
    moisture_pct = fields.Float(string='رطوبة التربة %', tracking=True,
                                help='آخر قراءة لرطوبة التربة (من الحساس أو يدويًا).')
    area_m2 = fields.Float(string='المساحة (م²)')
    last_run = fields.Datetime(string='آخر ريّ')
    next_run = fields.Datetime(compute='_compute_next', store=True)
    is_due = fields.Boolean(compute='_compute_next', store=True)
    water_m3 = fields.Float(string='إجمالي المياه (م³)')
    water_month_m3 = fields.Float(string='مياه هذا الشهر (م³)', compute='_compute_water_month')
    plant_ids = fields.One2many('care.cafm.agri.plant', 'zone_id', string='النباتات')
    plant_count = fields.Integer(string='عدد النباتات', compute='_compute_plant_count')
    log_ids = fields.One2many('care.cafm.agri.irrigation.log', 'zone_id', string='سجل الريّ')
    # client sign-off on the proposed irrigation plan
    client_plan_state = fields.Selection([
        ('pending', 'بانتظار موافقة العميل'), ('approved', 'معتمدة من العميل'), ('rejected', 'مرفوضة من العميل'),
    ], string='موافقة العميل على خطة الريّ', default='pending', tracking=True)
    client_plan_comment = fields.Char(string='تعليق العميل', tracking=True)
    client_plan_date = fields.Datetime(string='تاريخ الموافقة/الرفض', readonly=True)
    active = fields.Boolean(default=True)

    @api.depends('plant_ids')
    def _compute_plant_count(self):
        for z in self:
            z.plant_count = len(z.plant_ids)

    @api.depends('last_run', 'frequency')
    def _compute_next(self):
        now = fields.Datetime.now()
        for z in self:
            base = z.last_run or now
            z.next_run = base + FREQ.get(z.frequency, timedelta(days=1))
            z.is_due = z.next_run <= now

    def _compute_water_month(self):
        for z in self:
            first = fields.Date.context_today(z).replace(day=1)
            logs = z.log_ids.filtered(lambda l: l.date and l.date >= first)
            z.water_month_m3 = sum(logs.mapped('water_m3'))

    def action_run(self):
        for z in self:
            now = fields.Datetime.now()
            water = (z.flow_lpm * z.duration_min / 1000.0) if z.flow_lpm else 0.0
            z.last_run = now
            z.water_m3 += water
            z.valve_state = 'closed'
            self.env['care.cafm.agri.irrigation.log'].create({
                'zone_id': z.id, 'date': fields.Date.context_today(z),
                'duration_min': z.duration_min, 'water_m3': water,
                'moisture_after': z.moisture_pct,
            })
            z.message_post(body=_('💧 تم ريّ المنطقة — %.2f م³.') % water)

    def action_view_plants(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('نباتات %s') % self.name,
            'res_model': 'care.cafm.agri.plant', 'view_mode': 'tree,form,kanban',
            'domain': [('zone_id', '=', self.id)],
            'context': {'default_zone_id': self.id, 'default_facility_id': self.facility_id.id},
        }


class AgriIrrigationLog(models.Model):
    """Per-run irrigation reading — water audit & moisture trend."""
    _name = 'care.cafm.agri.irrigation.log'
    _description = 'Irrigation Log'
    _order = 'date desc, id desc'

    zone_id = fields.Many2one('care.cafm.agri.zone', string='المنطقة', required=True, ondelete='cascade', index=True)
    facility_id = fields.Many2one(related='zone_id.facility_id', store=True, string='المرفق')
    date = fields.Date(string='التاريخ', default=fields.Date.context_today, required=True)
    duration_min = fields.Integer(string='المدة (دقيقة)')
    water_m3 = fields.Float(string='المياه (م³)')
    moisture_before = fields.Float(string='الرطوبة قبل %')
    moisture_after = fields.Float(string='الرطوبة بعد %')
    done_by = fields.Many2one('hr.employee', string='المنفّذ')
    note = fields.Char(string='ملاحظة')


class AgriPlant(models.Model):
    """Plant/tree register — full monitoring: species, dimensions, inspections,
    irrigation zone, health trend and a complete works history."""
    _name = 'care.cafm.agri.plant'
    _description = 'Plant / Tree'
    _inherit = ['mail.thread']
    _order = 'facility_id, name'

    name = fields.Char(string='النبتة/الشجرة', required=True, tracking=True)
    code = fields.Char(string='الرمز/الوسم', copy=False, tracking=True,
                       help='وسم/باركود الشجرة للتعريف الميداني.')
    species_id = fields.Many2one('care.cafm.agri.species', string='النوع', tracking=True)
    category = fields.Selection(related='species_id.category', string='التصنيف', store=True)
    species = fields.Char(string='النوع (نص)')  # legacy free-text kept for back-compat
    image = fields.Image(string='صورة', max_width=1024, max_height=1024)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True, tracking=True)
    location_id = fields.Many2one('care.cafm.location', string='الموقع', tracking=True)
    zone_id = fields.Many2one('care.cafm.agri.zone', string='منطقة الريّ', tracking=True)
    gps = fields.Char(string='الإحداثيات (GPS)', help='خط العرض, خط الطول')
    planted_date = fields.Date(string='تاريخ الزرع', tracking=True)
    age_years = fields.Float(string='العمر (سنوات)', compute='_compute_age', store=True)
    height_m = fields.Float(string='الارتفاع (م)', tracking=True)
    trunk_cm = fields.Float(string='قطر الجذع (سم)', tracking=True)
    health = fields.Selection([
        ('good', 'جيدة'), ('fair', 'متوسطة'), ('poor', 'ضعيفة'), ('dead', 'ميتة/مُزالة'),
    ], string='الحالة الصحية', default='good', tracking=True)
    # Inspection tracking
    last_inspection = fields.Date(string='آخر فحص', tracking=True)
    next_inspection = fields.Date(string='الفحص القادم', tracking=True)
    inspection_overdue = fields.Boolean(string='فحص متأخّر', compute='_compute_overdue', search='_search_overdue')
    # Care schedule (from species)
    last_prune = fields.Date(string='آخر تقليم')
    next_prune = fields.Date(string='التقليم القادم', compute='_compute_care_due', store=True)
    last_fertilize = fields.Date(string='آخر تسميد')
    next_fertilize = fields.Date(string='التسميد القادم', compute='_compute_care_due', store=True)
    care_note = fields.Char(string='ملاحظات العناية')
    operation_ids = fields.One2many('care.cafm.agri.operation', 'plant_id', string='الأعمال')
    operation_count = fields.Integer(string='عدد الأعمال', compute='_compute_op_count')
    active = fields.Boolean(default=True)

    @api.depends('planted_date')
    def _compute_age(self):
        today = fields.Date.context_today(self)
        for p in self:
            p.age_years = round((today - p.planted_date).days / 365.0, 1) if p.planted_date else 0.0

    @api.depends('operation_ids')
    def _compute_op_count(self):
        for p in self:
            p.operation_count = len(p.operation_ids)

    @api.depends('last_prune', 'last_fertilize', 'species_id.prune_interval_days', 'species_id.fertilize_interval_days')
    def _compute_care_due(self):
        for p in self:
            pi = p.species_id.prune_interval_days or 0
            fi = p.species_id.fertilize_interval_days or 0
            p.next_prune = (p.last_prune + timedelta(days=pi)) if (p.last_prune and pi) else False
            p.next_fertilize = (p.last_fertilize + timedelta(days=fi)) if (p.last_fertilize and fi) else False

    def _compute_overdue(self):
        today = fields.Date.context_today(self)
        for p in self:
            p.inspection_overdue = bool(p.next_inspection and p.next_inspection < today)

    def _search_overdue(self, operator, value):
        today = fields.Date.context_today(self)
        recs = self.search([('next_inspection', '<', today)])
        want = (operator == '=' and value) or (operator == '!=' and not value)
        return [('id', 'in' if want else 'not in', recs.ids)]

    def action_view_operations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('أعمال %s') % self.name,
            'res_model': 'care.cafm.agri.operation', 'view_mode': 'tree,form',
            'domain': [('plant_id', '=', self.id)],
            'context': {'default_plant_id': self.id, 'default_facility_id': self.facility_id.id},
        }


class AgriOperation(models.Model):
    """Tree/plant works log — pruning, fertilizing, planting, pest control,
    removal and inspection. Each work updates the plant's care dates and can
    schedule the next occurrence. The heart of arboriculture ops."""
    _name = 'care.cafm.agri.operation'
    _description = 'Agri Operation / Tree Work'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char(string='المرجع', compute='_compute_name', store=True)
    plant_id = fields.Many2one('care.cafm.agri.plant', string='الشجرة/النبتة', ondelete='cascade', index=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True, tracking=True)
    zone_id = fields.Many2one('care.cafm.agri.zone', string='المنطقة')
    operation_type = fields.Selection([
        ('prune', 'تقليم'), ('fertilize', 'تسميد'), ('plant', 'زراعة'),
        ('transplant', 'نقل/إعادة زراعة'), ('pest', 'مكافحة آفات'),
        ('weed', 'إزالة أعشاب'), ('mulch', 'تغطية/فرش'),
        ('inspect', 'فحص'), ('remove', 'إزالة/قطع'), ('other', 'أخرى'),
    ], string='نوع العمل', default='prune', required=True, tracking=True)
    date = fields.Date(string='التاريخ', default=fields.Date.context_today, required=True, tracking=True)
    done_by = fields.Many2one('hr.employee', string='المنفّذ', tracking=True)
    material = fields.Char(string='المواد المستخدمة')
    quantity = fields.Float(string='الكمية')
    unit = fields.Char(string='الوحدة')
    cost = fields.Float(string='التكلفة')
    photo_before = fields.Image(string='صورة قبل', max_width=1024, max_height=1024)
    photo_after = fields.Image(string='صورة بعد', max_width=1024, max_height=1024)
    result = fields.Selection([
        ('done', 'مُنجز'), ('partial', 'جزئي'), ('failed', 'متعذّر'),
    ], string='النتيجة', default='done', tracking=True)
    next_due = fields.Date(string='الموعد القادم')
    note = fields.Text(string='ملاحظات')

    @api.depends('operation_type', 'plant_id', 'date')
    def _compute_name(self):
        labels = dict(self._fields['operation_type'].selection)
        for o in self:
            who = o.plant_id.name or (o.facility_id.name or '')
            o.name = '%s — %s' % (labels.get(o.operation_type, ''), who)

    @api.model_create_multi
    def create(self, vals_list):
        ops = super().create(vals_list)
        ops._apply_to_plant()
        return ops

    def _apply_to_plant(self):
        """Sync the plant's care dates from the work performed."""
        for o in self:
            p = o.plant_id
            if not p or o.result == 'failed':
                continue
            if o.operation_type == 'prune':
                p.last_prune = o.date
            elif o.operation_type == 'fertilize':
                p.last_fertilize = o.date
            elif o.operation_type == 'inspect':
                p.last_inspection = o.date
                if o.next_due:
                    p.next_inspection = o.next_due
            elif o.operation_type == 'remove':
                p.health = 'dead'
                p.active = False


class AgriTreatment(models.Model):
    """Pesticide/fertilizer application log (compliance/safety)."""
    _name = 'care.cafm.agri.treatment'
    _description = 'Agri Treatment Log'
    _order = 'date desc, id desc'

    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True)
    location_id = fields.Many2one('care.cafm.location', string='الموقع')
    treatment_type = fields.Selection([
        ('pesticide', 'مبيد'), ('fertilizer', 'سماد'), ('other', 'أخرى'),
    ], string='النوع', default='fertilizer', required=True)
    product = fields.Char(string='المنتج')
    quantity = fields.Float(string='الكمية')
    unit = fields.Char(string='الوحدة')
    date = fields.Date(string='التاريخ', default=fields.Date.context_today, required=True)
    applied_by = fields.Many2one('hr.employee', string='المنفّذ')
    note = fields.Char()
