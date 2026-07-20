# -*- coding: utf-8 -*-
"""Completes the CAFM operating cycle to match the mockup:
 - Service Requests (طلبات الخدمة): client/intake → triage → convert to a work order.
 - Assets (الأصول): the equipment register per location, linked to work orders.
 - PPM plans (الصيانة الوقائية): recurring schedules that auto-generate work orders.
"""
import base64
from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class CafmAsset(models.Model):
    _name = 'care.cafm.asset'
    _description = 'CAFM Asset'
    _inherit = ['mail.thread']
    _order = 'facility_id, name'

    name = fields.Char(string='الأصل', required=True, tracking=True, translate=True)
    # ---- who owns it decides who may change it ---------------------------
    # A chiller CARE installed and a chiller the hospital already owned are
    # not the same record. The client maintains their own equipment; CARE
    # equipment is ours to describe, and a client edit to it would quietly
    # rewrite our own asset register.
    ownership = fields.Selection([
        ('care', 'CARE-owned'), ('client', 'Client-owned'),
    ], string='Ownership', default='care', required=True, tracking=True, index=True)
    client_editable = fields.Boolean(string='Client may edit',
                                     compute='_compute_client_editable')

    # Scanning beats searching when you are standing in front of the thing.
    nfc_uid = fields.Char(string='NFC tag', copy=False, index=True, tracking=True)
    qr_code = fields.Char(string='QR code', compute='_compute_qr_code', store=True,
                          index=True)

    @api.depends('code')
    def _compute_qr_code(self):
        # Odoo refuses a compute that depends on id, so fall back on the id
        # inside the body instead — a new record simply has no QR until saved.
        for a in self:
            a.qr_code = a.code or ('AST-%s' % a.id if a.id else False)

    def _compute_client_editable(self):
        mgr = self.env.user.has_group('base.group_system') or \
            self.env.user.has_group('base.group_erp_manager')
        for a in self:
            a.client_editable = mgr or a.ownership == 'client'

    # Fields that describe what the asset IS, as opposed to notes about its
    # condition. A client may keep the latter on any asset.
    CORE_FIELDS = ('name', 'code', 'category', 'ownership', 'serial',
                   'model', 'brand', 'purchase_date', 'warranty_end',
                   'facility_id', 'location_id')

    def write(self, vals):
        if not self.env.context.get('asset_owner_write'):
            staff = self.env.user.has_group('base.group_system') or \
                self.env.user.has_group('base.group_erp_manager')
            if not staff:
                touched = [f for f in vals if f in self.CORE_FIELDS]
                blocked = self.filtered(lambda a: a.ownership == 'care')
                if touched and blocked:
                    raise UserError(_(
                        'This asset belongs to CARE. You can add notes and '
                        'report faults on it, but its details are maintained '
                        'by CARE.'))
        return super().write(vals)

    def unlink(self):
        staff = self.env.user.has_group('base.group_system') or \
            self.env.user.has_group('base.group_erp_manager')
        if not staff and self.filtered(lambda a: a.ownership == 'care'):
            raise UserError(_('A CARE-owned asset cannot be deleted here.'))
        return super().unlink()


    code = fields.Char(string='الرمز', copy=False, index=True, tracking=True,
                       default=lambda s: _('جديد'))
    category = fields.Selection([
        ('hvac', 'تكييف وتهوية'), ('electrical', 'كهرباء'), ('plumbing', 'سباكة'),
        ('elevator', 'مصاعد'), ('fire', 'إطفاء وإنذار'), ('generator', 'مولّدات'),
        ('cctv', 'مراقبة'), ('furniture', 'أثاث'), ('other', 'أخرى'),
    ], string='الفئة', default='other', tracking=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True, tracking=True, ondelete='cascade')
    location_id = fields.Many2one('care.cafm.location', string='الموقع', tracking=True,
                                  domain="[('facility_id','=',facility_id)]")
    building_id = fields.Many2one(related='location_id.building_id', store=True, string='المبنى')
    ownership = fields.Selection([
        ('company', 'تابع لشركة كير (لنا)'),
        ('client', 'تابع للعميل'),
    ], string='ملكية الأصل', default='company', required=True, tracking=True,
        help='تابع لكير: يُختار من نظام أصولنا. تابع للعميل: يُدخل رقمه التسلسلي.')
    company_asset_id = fields.Many2one('account.asset', string='من نظام أصول كير', tracking=True,
                                       help='اختر الأصل من نظام الأصول لدينا (عند ملكية الشركة).')
    serial = fields.Char(string='الرقم التسلسلي', tracking=True)
    barcode = fields.Char(string='الباركود', copy=False, index=True, tracking=True,
                          help='باركود الأصل — يُمسح للوصول السريع لسجل الأصل.')
    qr_value = fields.Char(string='قيمة QR', compute='_compute_qr', store=True,
                           help='قيمة رمز QR (رمز الأصل) — تُطبع على ملصق الأصل.')
    qr_image = fields.Binary(string='رمز QR', compute='_compute_qr_image')
    brand = fields.Char(string='الماركة', tracking=True)
    model_name = fields.Char(string='الموديل', tracking=True)
    install_date = fields.Date(string='تاريخ التركيب', tracking=True)
    warranty_end = fields.Date(string='انتهاء الضمان', tracking=True)
    image = fields.Image(string='صورة الأصل', max_width=1024, max_height=1024)
    last_inspection_date = fields.Date(string='آخر فحص', tracking=True)
    next_inspection_date = fields.Date(string='الفحص القادم', tracking=True)
    last_audit_date = fields.Date(string='آخر جرد', tracking=True)
    audit_note = fields.Char(string='ملاحظة الجرد')
    status = fields.Selection([
        ('operational', 'يعمل'), ('maintenance', 'تحت الصيانة'),
        ('faulty', 'معطّل'), ('retired', 'خارج الخدمة'),
    ], string='الحالة', default='operational', tracking=True)
    notes = fields.Text(string='ملاحظات')
    workorder_ids = fields.One2many('care.cafm.workorder', 'cafm_asset_id', string='أوامر العمل')
    workorder_count = fields.Integer(compute='_compute_wo')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def _compute_wo(self):
        for rec in self:
            rec.workorder_count = len(rec.workorder_ids)

    @api.depends('code')
    def _compute_qr(self):
        for rec in self:
            rec.qr_value = 'CAFM-ASSET:%s' % (rec.code or rec.id or '')

    @api.depends('qr_value')
    def _compute_qr_image(self):
        Report = self.env['ir.actions.report']
        for rec in self:
            try:
                png = Report.barcode('QR', rec.qr_value or (rec.code or 'CAFM'), width=220, height=220)
                rec.qr_image = base64.b64encode(png)
            except Exception:
                rec.qr_image = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code') or vals['code'] == _('جديد'):
                vals['code'] = self.env['ir.sequence'].next_by_code('care.cafm.asset') or _('AST/%s') % len(self.search([]))
        recs = super().create(vals_list)
        for rec in recs:
            if not rec.barcode:
                rec.barcode = rec.code
        return recs

    def action_view_workorders(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('أوامر عمل %s') % self.name,
                'res_model': 'care.cafm.workorder', 'view_mode': 'tree,form',
                'domain': [('cafm_asset_id', '=', self.id)], 'context': {'default_cafm_asset_id': self.id,
                                                                     'default_facility_id': self.facility_id.id}}


class CafmRequest(models.Model):
    _name = 'care.cafm.service.request'
    _description = 'CAFM Service Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    title = fields.Char(string='الطلب', required=True, tracking=True)
    description = fields.Text(string='الوصف')
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True, tracking=True)
    location_id = fields.Many2one('care.cafm.location', string='الموقع', tracking=True,
                                  domain="[('facility_id','=',facility_id)]")
    asset_id = fields.Many2one('care.cafm.asset', string='الأصل', tracking=True,
                               domain="[('facility_id','=',facility_id)]")
    service_id = fields.Many2one('care.cafm.service', string='الخدمة', tracking=True)
    requested_hours = fields.Float(string='عدد الساعات المطلوبة', tracking=True,
                                   help='عدد ساعات الخدمة المطلوبة من العميل.')
    specifications = fields.Text(string='المواصفات الكاملة',
                                 help='مواصفات وتفاصيل تنفيذ الخدمة كما يحدّدها العميل.')
    partner_id = fields.Many2one('res.partner', string='العميل/الجهة', tracking=True)
    requested_by = fields.Many2one('res.users', string='مقدّم الطلب', default=lambda s: s.env.user, tracking=True)
    request_datetime = fields.Datetime(string='وقت الطلب', default=fields.Datetime.now, tracking=True)
    priority = fields.Selection([
        ('0', 'عادية'), ('1', 'متوسطة'), ('2', 'عالية'), ('3', 'عاجلة'),
    ], string='الأولوية', default='1', tracking=True)
    state = fields.Selection([
        ('new', 'جديد'), ('in_review', 'قيد المراجعة'), ('converted', 'حُوِّل لأمر عمل'),
        ('rejected', 'مرفوض'), ('closed', 'مغلق'),
    ], default='new', tracking=True)
    workorder_id = fields.Many2one('care.cafm.workorder', string='أمر العمل', readonly=True, copy=False)
    reject_reason = fields.Char(string='سبب الرفض')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.cafm.service.request') or '/'
        return super().create(vals_list)

    def action_review(self):
        self.write({'state': 'in_review'})

    def action_convert(self):
        """Turn the request into a work order — the core 'request → closure' path."""
        WO = self.env['care.cafm.workorder']
        for rec in self:
            if rec.workorder_id:
                raise UserError(_('حُوِّل هذا الطلب مسبقاً.'))
            service = rec.service_id or self.env['care.cafm.service'].search([], limit=1)
            wo = WO.create({
                'title': rec.title, 'facility_id': rec.facility_id.id,
                'location_id': rec.location_id.id or False, 'service_id': service.id,
                'cafm_asset_id': rec.asset_id.id or False, 'priority': rec.priority,
                'description': rec.description or False, 'wo_type': 'reactive',
            })
            rec.write({'state': 'converted', 'workorder_id': wo.id})
            rec.message_post(body=_('تم تحويل الطلب إلى أمر العمل %s.') % wo.name)
        return True

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_open_workorder(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'care.cafm.workorder',
                'res_id': self.workorder_id.id, 'view_mode': 'form'}


class CafmPPM(models.Model):
    _name = 'care.cafm.ppm'
    _description = 'CAFM Preventive Maintenance Plan'
    _inherit = ['mail.thread']
    _order = 'next_date'

    name = fields.Char(string='الخطة', required=True, tracking=True, translate=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True, tracking=True)
    location_id = fields.Many2one('care.cafm.location', string='الموقع', tracking=True,
                                  domain="[('facility_id','=',facility_id)]")
    asset_id = fields.Many2one('care.cafm.asset', string='الأصل', tracking=True,
                               domain="[('facility_id','=',facility_id)]")
    service_id = fields.Many2one('care.cafm.service', string='الخدمة', required=True, tracking=True)
    interval_number = fields.Integer(string='التكرار كل', default=1, required=True, tracking=True)
    interval_unit = fields.Selection([
        ('days', 'أيام'), ('weeks', 'أسابيع'), ('months', 'أشهر'),
    ], string='الوحدة', default='months', required=True, tracking=True)
    expected_minutes = fields.Integer(string='المدة المقدّرة (دقيقة)', default=60)
    employee_id = fields.Many2one('hr.employee', string='يُسنَد إلى', tracking=True)
    next_date = fields.Date(string='الاستحقاق التالي', default=fields.Date.today, required=True, tracking=True)
    last_generated = fields.Date(string='آخر توليد', readonly=True, copy=False)
    generated_count = fields.Integer(string='عدد الأوامر المولّدة', readonly=True, copy=False)
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def _delta(self):
        self.ensure_one()
        return {'days': relativedelta(days=self.interval_number),
                'weeks': relativedelta(weeks=self.interval_number),
                'months': relativedelta(months=self.interval_number)}[self.interval_unit]

    def action_generate_now(self):
        for rec in self:
            rec._generate_wo()

    def _generate_wo(self):
        self.ensure_one()
        wo = self.env['care.cafm.workorder'].create({
            'title': _('صيانة وقائية: %s') % self.name,
            'facility_id': self.facility_id.id, 'location_id': self.location_id.id or False,
            'service_id': self.service_id.id, 'cafm_asset_id': self.asset_id.id or False,
            'employee_id': self.employee_id.id or False, 'wo_type': 'preventive',
            'expected_minutes': self.expected_minutes,
            'state': 'assigned' if self.employee_id else 'new',
        })
        self.write({'last_generated': fields.Date.today(),
                    'generated_count': self.generated_count + 1,
                    'next_date': (fields.Date.today() + self._delta())})
        self.message_post(body=_('وُلّد أمر عمل وقائي %s.') % wo.name)
        return wo

    @api.model
    def _cron_generate(self):
        today = fields.Date.today()
        for plan in self.search([('active', '=', True), ('next_date', '<=', today)]):
            try:
                plan._generate_wo()
            except Exception:
                continue
