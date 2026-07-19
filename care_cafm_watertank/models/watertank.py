# -*- coding: utf-8 -*-
"""Water tank cleaning, which is a compliance record before it is a job.

Nobody inspects a clean tank. They inspect the paperwork: when was it last
done, by whom, with what, and what did the lab say about the water afterwards.
So the cleaning record carries its own certificate number and lab result, and
the next due date is derived from the last completed clean rather than typed in
and forgotten.
"""
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WaterTank(models.Model):
    _name = 'care.tank.tank'
    _description = 'خزان مياه'
    _inherit = ['mail.thread']
    _order = 'facility_id, code'

    name = fields.Char(string='الخزان', compute='_compute_name', store=True)
    code = fields.Char(string='رقم الخزان', required=True, tracking=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True,
                                  tracking=True, index=True)
    location_id = fields.Many2one('care.cafm.location', string='الموقع', tracking=True)
    position = fields.Selection([
        ('roof', 'علوي (سطح)'), ('ground', 'أرضي'), ('underground', 'تحت الأرض'),
    ], string='الموقع', default='roof', required=True, tracking=True)
    material = fields.Selection([
        ('grp', 'فايبر جلاس GRP'), ('polyethylene', 'بولي إيثيلين'),
        ('concrete', 'خرساني'), ('steel', 'حديد مجلفن'), ('stainless', 'ستانلس ستيل'),
    ], string='الخامة', default='grp', tracking=True)
    capacity_gal = fields.Float(string='السعة (جالون)', tracking=True)
    use = fields.Selection([
        ('potable', 'مياه شرب'), ('domestic', 'استخدام عام'), ('fire', 'مكافحة حريق'),
        ('irrigation', 'ري'),
    ], string='الاستخدام', default='domestic', required=True, tracking=True)
    cycle_months = fields.Integer(string='دورة التنظيف (شهر)', default=6, required=True,
                                  tracking=True,
                                  help='المتعارف عليه ٦ أشهر لمياه الشرب.')

    cleaning_ids = fields.One2many('care.tank.cleaning', 'tank_id', string='عمليات التنظيف')
    last_cleaned = fields.Date(string='آخر تنظيف', compute='_compute_cycle', store=True)
    next_due = fields.Date(string='التنظيف القادم', compute='_compute_cycle', store=True, index=True)
    days_left = fields.Integer(string='المتبقّي (يوم)', compute='_compute_days')
    status = fields.Selection([
        ('ok', 'ضمن الدورة'), ('due_soon', 'يستحق قريبًا'), ('overdue', 'متأخر'),
        ('never', 'لم يُنظَّف بعد'),
    ], string='حالة الدورة', compute='_compute_days', store=True, index=True)
    last_lab = fields.Selection([
        ('pass', 'مطابقة'), ('fail', 'غير مطابقة'),
    ], string='آخر نتيجة مخبرية', compute='_compute_cycle', store=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [('code_facility_uniq', 'unique(code, facility_id)',
                         'رقم الخزان مستخدم في هذا المرفق.')]

    @api.depends('code', 'position', 'capacity_gal')
    def _compute_name(self):
        pos = dict(self._fields['position'].selection)
        for t in self:
            t.name = '%s — %s%s' % (t.code or '', pos.get(t.position, ''),
                                    ' · %d جالون' % t.capacity_gal if t.capacity_gal else '')

    @api.depends('cleaning_ids.clean_date', 'cleaning_ids.state', 'cycle_months',
                 'cleaning_ids.lab_result')
    def _compute_cycle(self):
        for t in self:
            done = t.cleaning_ids.filtered(lambda c: c.state == 'done' and c.clean_date)
            last = done.sorted('clean_date', reverse=True)[:1]
            t.last_cleaned = last.clean_date if last else False
            t.last_lab = last.lab_result if last else False
            # 30-day months are close enough for a 6-month cycle and avoid a
            # dependency just to add months.
            t.next_due = (last.clean_date + timedelta(days=30 * (t.cycle_months or 6))
                          if last else False)

    @api.depends('next_due', 'last_cleaned')
    def _compute_days(self):
        today = fields.Date.context_today(self)
        for t in self:
            if not t.last_cleaned:
                t.days_left, t.status = 0, 'never'
                continue
            t.days_left = (t.next_due - today).days if t.next_due else 0
            t.status = ('overdue' if t.days_left < 0
                        else 'due_soon' if t.days_left <= 30 else 'ok')

    def action_start_cleaning(self):
        """Open a cleaning already carrying the standard step list, so the
        record cannot quietly omit the steps that make it a compliant clean."""
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'care.tank.cleaning',
                'view_mode': 'form',
                'context': {'default_tank_id': self.id,
                            'default_facility_id': self.facility_id.id}}

    @api.model
    def _cron_due(self):
        today = fields.Date.context_today(self)
        due = self.search(['|', ('status', '=', 'overdue'),
                           ('next_due', '<=', today + timedelta(days=30))])
        if not due or 'care.cafm.notification' not in self.env:
            return True
        staff = self.env['res.users'].sudo().search(
            [('groups_id', 'in', self.env.ref('base.group_erp_manager').id)], limit=8)
        for t in due:
            late = t.status == 'overdue'
            try:
                self.env['care.cafm.notification'].sudo().push(
                    staff,
                    _('🚰 تنظيف خزان %s') % (_('متأخر') if late else _('يستحق قريبًا')),
                    '%s — %s' % (t.name, t.facility_id.name or ''),
                    ntype='alert' if late else 'warning')
            except Exception:
                pass
        return True


class TankCleaning(models.Model):
    """One documented clean. The certificate and the lab result are the point."""
    _name = 'care.tank.cleaning'
    _description = 'تنظيف خزان'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'clean_date desc, id desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    tank_id = fields.Many2one('care.tank.tank', string='الخزان', required=True,
                              ondelete='cascade', index=True, tracking=True)
    facility_id = fields.Many2one(related='tank_id.facility_id', store=True, index=True)
    clean_date = fields.Date(string='تاريخ التنظيف', default=fields.Date.context_today,
                             required=True, tracking=True, index=True)
    crew_id = fields.Many2one('hr.employee', string='المنفّذ', tracking=True)
    state = fields.Selection([
        ('draft', 'قيد التنفيذ'), ('done', 'مكتمل'), ('cancelled', 'ملغى'),
    ], string='الحالة', default='draft', required=True, tracking=True)

    # the steps that make it a compliant clean rather than a rinse
    step_drained = fields.Boolean(string='تفريغ الخزان وعزل خط التغذية')
    step_sediment = fields.Boolean(string='إزالة الرواسب')
    step_scrubbed = fields.Boolean(string='تنظيف الجدران والقاع')
    step_disinfected = fields.Boolean(string='تعقيم بالكلور المخفّف')
    step_rinsed = fields.Boolean(string='شطف كامل حتى زوال أثر الكلور')
    step_refilled = fields.Boolean(string='إعادة التعبئة')
    chlorine_ppm = fields.Float(string='تركيز الكلور المستخدم (ppm)', default=50.0,
                                help='المتعارف عليه 50 ppm لمدة ساعة تلامس.')
    contact_minutes = fields.Integer(string='زمن التلامس (دقيقة)', default=60)
    residual_ppm = fields.Float(string='الكلور المتبقي بعد الشطف (ppm)',
                                help='يجب أن يعود لمستوى الشبكة الطبيعي قبل التشغيل.')

    lab_sample_taken = fields.Boolean(string='أُخذت عيّنة مخبرية')
    lab_result = fields.Selection([
        ('pass', 'مطابقة للمواصفة'), ('fail', 'غير مطابقة'),
    ], string='نتيجة التحليل', tracking=True)
    lab_reference = fields.Char(string='رقم التقرير المخبري')
    certificate_no = fields.Char(string='رقم شهادة التنظيف', copy=False, readonly=True,
                                 tracking=True)
    findings = fields.Text(string='الملاحظات')
    completeness = fields.Integer(string='اكتمال الخطوات %', compute='_compute_complete', store=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    STEPS = ['step_drained', 'step_sediment', 'step_scrubbed',
             'step_disinfected', 'step_rinsed', 'step_refilled']

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.tank.cleaning') or '/'
        return super().create(vals_list)

    @api.depends(*STEPS)
    def _compute_complete(self):
        for c in self:
            done = sum(1 for f in self.STEPS if c[f])
            c.completeness = int(100.0 * done / len(self.STEPS))

    def action_done(self):
        """A clean is only complete when every step is, because the certificate
        this issues is what a client shows an inspector."""
        for c in self:
            missing = [self._fields[f].string for f in self.STEPS if not c[f]]
            if missing:
                raise UserError(_('لا يمكن إصدار الشهادة قبل إتمام كل الخطوات.\nالمتبقّي: %s')
                                % '، '.join(missing))
            if c.lab_sample_taken and not c.lab_result:
                raise UserError(_('سُجّلت عيّنة مخبرية دون نتيجة — أدخل النتيجة أولًا.'))
            if c.lab_result == 'fail':
                raise UserError(_('نتيجة التحليل غير مطابقة — يجب إعادة التنظيف قبل الاعتماد.'))
            c.certificate_no = c.certificate_no or (
                self.env['ir.sequence'].next_by_code('care.tank.certificate') or c.name)
            c.state = 'done'
            c._notify_client()

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def _notify_client(self):
        self.ensure_one()
        if 'care.cafm.notification' not in self.env:
            return
        client = self.env['care.cafm.client'].sudo().search(
            [('partner_id', '=', self.facility_id.partner_id.id)], limit=1)
        if not client or not client.user_ids:
            return
        try:
            self.env['care.cafm.notification'].sudo().push(
                client.user_ids, _('🚰 تم تنظيف خزان وإصدار الشهادة'),
                '%s — شهادة %s' % (self.tank_id.name, self.certificate_no or ''),
                ntype='info')
        except Exception:
            pass
