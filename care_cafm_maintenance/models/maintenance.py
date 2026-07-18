# -*- coding: utf-8 -*-
"""Professional maintenance management for CARE CAFM.

Covers the full maintenance lifecycle: departments & trades, spare-parts store,
fault/breakdown reports (→ work orders), and periodic inspection schedules with
checklists. Integrates with the existing care.cafm.asset / facility / work-order
models rather than duplicating them."""
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError

FREQ = {'daily': 1, 'weekly': 7, 'biweekly': 14, 'monthly': 30,
        'quarterly': 90, 'semiannual': 182, 'annual': 365}

# the maintenance trades a technician can hold — drives assignment/filtering.
TRADES = [
    ('electrician', 'كهربائي'), ('plumber', 'سبّاك'), ('carpenter', 'نجّار'),
    ('hvac', 'فني تكييف'), ('mechanic', 'ميكانيكي'), ('welder', 'لحّام'),
    ('painter', 'دهّان'), ('mason', 'بنّاء'), ('technician', 'فني عام'),
    ('elevator', 'فني مصاعد'), ('fire', 'فني إطفاء وإنذار'),
]


class MaintDepartment(models.Model):
    """A maintenance section/trade unit (electrical, mechanical, HVAC, …)."""
    _name = 'care.cafm.maint.department'
    _description = 'قسم الصيانة'
    _order = 'name'

    name = fields.Char(string='القسم', required=True, translate=True)
    code = fields.Char(string='الرمز')
    trade = fields.Selection(TRADES, string='التخصص الرئيسي')
    color = fields.Integer(string='لون')
    head_id = fields.Many2one('hr.employee', string='رئيس القسم')
    facility_ids = fields.Many2many('care.cafm.facility', string='المرافق المخدومة')
    description = fields.Text(string='الوصف')
    active = fields.Boolean(default=True)
    fault_count = fields.Integer(compute='_compute_counts', string='الأعطال')
    tech_count = fields.Integer(compute='_compute_counts', string='الفنيون')

    def _compute_counts(self):
        Fault = self.env['care.cafm.maint.fault']
        Emp = self.env['hr.employee']
        for d in self:
            d.fault_count = Fault.search_count([('department_id', '=', d.id)])
            d.tech_count = Emp.search_count([('maint_department_id', '=', d.id)])


class MaintPart(models.Model):
    """A maintenance spare part with stock levels — the parts store."""
    _name = 'care.cafm.maint.part'
    _description = 'قطعة غيار'
    _order = 'name'

    name = fields.Char(string='القطعة', required=True, translate=True)
    code = fields.Char(string='الرمز/الكود', copy=False, index=True)
    category = fields.Selection([
        ('electrical', 'كهرباء'), ('plumbing', 'سباكة'), ('hvac', 'تكييف'),
        ('mechanical', 'ميكانيكا'), ('consumable', 'مستهلكات'),
        ('tools', 'عدد وأدوات'), ('other', 'أخرى'),
    ], string='الفئة', default='other', required=True)
    department_id = fields.Many2one('care.cafm.maint.department', string='القسم')
    uom_name = fields.Char(string='الوحدة', default='قطعة')
    on_hand = fields.Float(string='المتوفر')
    min_qty = fields.Float(string='الحد الأدنى', default=1.0)
    unit_cost = fields.Float(string='تكلفة الوحدة')
    location = fields.Char(string='موقع التخزين')
    supplier = fields.Char(string='المورّد')
    barcode = fields.Char(string='الباركود', copy=False)
    stock_value = fields.Float(string='قيمة المخزون', compute='_compute_value', store=True)
    low_stock = fields.Boolean(string='مخزون منخفض', compute='_compute_low', store=True, search='_search_low')
    active = fields.Boolean(default=True)

    @api.depends('on_hand', 'unit_cost')
    def _compute_value(self):
        for p in self:
            p.stock_value = (p.on_hand or 0.0) * (p.unit_cost or 0.0)

    @api.depends('on_hand', 'min_qty')
    def _compute_low(self):
        for p in self:
            p.low_stock = (p.on_hand or 0.0) <= (p.min_qty or 0.0)

    def _search_low(self, operator, value):
        recs = self.search([]).filtered('low_stock')
        want = (operator == '=' and value) or (operator == '!=' and not value)
        return [('id', 'in' if want else 'not in', recs.ids)]


class MaintFault(models.Model):
    """A reported fault/breakdown — the intake for corrective maintenance. Can be
    diagnosed, assigned to a technician and converted into a work order."""
    _name = 'care.cafm.maint.fault'
    _description = 'بلاغ عطل'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'reported_date desc, id desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    title = fields.Char(string='العطل', required=True, tracking=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True, tracking=True)
    location_id = fields.Many2one('care.cafm.location', string='الموقع', tracking=True)
    asset_id = fields.Many2one('care.cafm.asset', string='الأصل/المعدّة', tracking=True,
                               domain="[('facility_id','=',facility_id)]")
    department_id = fields.Many2one('care.cafm.maint.department', string='القسم', tracking=True)
    trade = fields.Selection(TRADES, string='التخصص المطلوب')
    severity = fields.Selection([
        ('low', 'منخفضة'), ('medium', 'متوسطة'), ('high', 'عالية'), ('critical', 'حرجة'),
    ], string='الخطورة', default='medium', required=True, tracking=True)
    description = fields.Text(string='وصف العطل')
    reported_by = fields.Many2one('res.users', string='المُبلِّغ', default=lambda s: s.env.user)
    reporter_name = fields.Char(string='اسم المُبلِّغ')
    reported_date = fields.Datetime(string='وقت البلاغ', default=fields.Datetime.now, tracking=True)
    assignee_id = fields.Many2one('hr.employee', string='الفني المُسنَد', tracking=True)
    state = fields.Selection([
        ('reported', 'مُبلَّغ'), ('diagnosed', 'تم التشخيص'), ('in_progress', 'قيد الإصلاح'),
        ('resolved', 'تم الإصلاح'), ('closed', 'مغلق'), ('cancelled', 'ملغى'),
    ], string='الحالة', default='reported', tracking=True, index=True)
    diagnosis = fields.Text(string='التشخيص')
    resolution = fields.Text(string='الإجراء التصحيحي')
    down_since = fields.Datetime(string='متعطّل منذ')
    restored_at = fields.Datetime(string='أُعيد التشغيل')
    downtime_hours = fields.Float(string='مدة التعطّل (ساعة)', compute='_compute_downtime', store=True)
    workorder_id = fields.Many2one('care.cafm.workorder', string='أمر العمل', readonly=True, copy=False)
    part_line_ids = fields.One2many('care.cafm.maint.fault.part', 'fault_id', string='قطع الغيار المستخدمة')
    parts_cost = fields.Float(string='تكلفة القطع', compute='_compute_parts_cost', store=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('down_since', 'restored_at')
    def _compute_downtime(self):
        for f in self:
            if f.down_since and f.restored_at and f.restored_at > f.down_since:
                f.downtime_hours = round((f.restored_at - f.down_since).total_seconds() / 3600.0, 1)
            else:
                f.downtime_hours = 0.0

    @api.depends('part_line_ids.subtotal')
    def _compute_parts_cost(self):
        for f in self:
            f.parts_cost = sum(f.part_line_ids.mapped('subtotal'))

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', '/') == '/':
                v['name'] = self.env['ir.sequence'].next_by_code('care.cafm.maint.fault') or '/'
        return super().create(vals_list)

    def action_make_workorder(self):
        self.ensure_one()
        if self.workorder_id:
            raise UserError(_('حُوِّل هذا البلاغ مسبقاً إلى أمر عمل.'))
        service = self.env['care.cafm.service'].search([('service_type', '=', 'maintenance')], limit=1) \
            or self.env['care.cafm.service'].search([], limit=1)
        if not service:
            raise UserError(_('لا توجد خدمة صيانة معرّفة.'))
        prio = {'low': '0', 'medium': '1', 'high': '2', 'critical': '3'}.get(self.severity, '1')
        wo = self.env['care.cafm.workorder'].create({
            'title': self.title, 'facility_id': self.facility_id.id,
            'location_id': self.location_id.id or False, 'service_id': service.id,
            'cafm_asset_id': self.asset_id.id or False, 'employee_id': self.assignee_id.id or False,
            'wo_type': 'reactive', 'priority': prio,
            'description': self.description or False,
        })
        self.write({'workorder_id': wo.id, 'state': 'in_progress'})
        self.message_post(body=_('حُوِّل البلاغ إلى أمر العمل %s.') % wo.name)
        return wo

    def action_resolve(self):
        self.write({'state': 'resolved', 'restored_at': fields.Datetime.now()})

    def action_close(self):
        self.write({'state': 'closed'})


class MaintFaultPart(models.Model):
    """Spare parts consumed on a fault repair — feeds cost + stock depletion."""
    _name = 'care.cafm.maint.fault.part'
    _description = 'قطعة على بلاغ'

    fault_id = fields.Many2one('care.cafm.maint.fault', required=True, ondelete='cascade')
    part_id = fields.Many2one('care.cafm.maint.part', string='القطعة', required=True)
    quantity = fields.Float(string='الكمية', default=1.0)
    unit_cost = fields.Float(related='part_id.unit_cost', string='تكلفة الوحدة')
    subtotal = fields.Float(string='الإجمالي', compute='_compute_sub', store=True)

    @api.depends('quantity', 'unit_cost')
    def _compute_sub(self):
        for l in self:
            l.subtotal = (l.quantity or 0.0) * (l.unit_cost or 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for l in lines:  # deplete stock on consumption
            if l.part_id and l.quantity:
                l.part_id.on_hand = max(0.0, (l.part_id.on_hand or 0.0) - l.quantity)
        return lines


class MaintInspection(models.Model):
    """A periodic inspection schedule for an asset/location, with a checklist and
    a next-due date the dashboard tracks."""
    _name = 'care.cafm.maint.inspection'
    _description = 'فحص دوري'
    _inherit = ['mail.thread']
    _order = 'next_date'

    name = fields.Char(string='الفحص', required=True, tracking=True, translate=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True, tracking=True)
    location_id = fields.Many2one('care.cafm.location', string='الموقع')
    asset_id = fields.Many2one('care.cafm.asset', string='الأصل/المعدّة',
                               domain="[('facility_id','=',facility_id)]")
    department_id = fields.Many2one('care.cafm.maint.department', string='القسم')
    assignee_id = fields.Many2one('hr.employee', string='الفني المسؤول')
    frequency = fields.Selection([
        ('daily', 'يومي'), ('weekly', 'أسبوعي'), ('biweekly', 'كل أسبوعين'),
        ('monthly', 'شهري'), ('quarterly', 'ربع سنوي'), ('semiannual', 'نصف سنوي'), ('annual', 'سنوي'),
    ], string='التردّد', default='monthly', required=True, tracking=True)
    last_date = fields.Date(string='آخر فحص', tracking=True)
    next_date = fields.Date(string='الفحص القادم', compute='_compute_next', store=True)
    is_due = fields.Boolean(string='مستحق', compute='_compute_next', store=True)
    checklist_ids = fields.One2many('care.cafm.maint.inspection.item', 'inspection_id', string='بنود الفحص')
    last_result = fields.Selection([
        ('pass', 'مطابق'), ('minor', 'ملاحظات بسيطة'), ('fail', 'فشل'),
    ], string='آخر نتيجة', tracking=True)
    notes = fields.Text(string='ملاحظات')
    active = fields.Boolean(default=True)

    @api.depends('last_date', 'frequency')
    def _compute_next(self):
        today = fields.Date.today()
        for r in self:
            base = r.last_date or today
            r.next_date = base + timedelta(days=FREQ.get(r.frequency, 30))
            r.is_due = r.next_date <= today

    def action_mark_done(self, result='pass'):
        self.write({'last_date': fields.Date.today(), 'last_result': result})


class MaintInspectionItem(models.Model):
    """A checklist item on an inspection schedule (its default template)."""
    _name = 'care.cafm.maint.inspection.item'
    _description = 'بند فحص'
    _order = 'sequence, id'

    inspection_id = fields.Many2one('care.cafm.maint.inspection', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string='البند', required=True)
    result = fields.Selection([
        ('ok', 'سليم'), ('fail', 'يحتاج إصلاح'), ('na', 'لا ينطبق'),
    ], string='النتيجة')
    note = fields.Char(string='ملاحظة')


class HrEmployeeMaint(models.Model):
    """Maintenance trade/department on the employee record — so a fault can be
    assigned to the right specialist (carpenter, electrician, …)."""
    _inherit = 'hr.employee'

    maint_trade = fields.Selection(TRADES, string='تخصّص الصيانة')
    maint_department_id = fields.Many2one('care.cafm.maint.department', string='قسم الصيانة')
