# -*- coding: utf-8 -*-
"""Disinfection, where the contact time is the service.

Wiping a surface with disinfectant and drying it immediately does nothing —
the product has to sit for its dwell time to kill anything. That single number
is what separates disinfection from wiping, and it is the one thing nobody
records. So it is a required field here, checked against the product's own
requirement, and a round that did not observe it is marked as such rather than
quietly counted as done.
"""
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DisinfectProduct(models.Model):
    _name = 'care.disinfect.product'
    _description = 'مطهّر معتمد'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='الاسم التجاري', required=True, tracking=True)
    name_en = fields.Char(string='الاسم بالإنجليزية')
    active_ingredient = fields.Char(string='المادة الفعّالة', required=True, tracking=True)
    registration = fields.Char(string='رقم التسجيل', tracking=True)
    dilution = fields.Char(string='التخفيف المعتمد')
    contact_minutes = fields.Integer(string='زمن التلامس المطلوب (دقيقة)', default=1,
                                     required=True, tracking=True,
                                     help='المدة التي يجب أن يبقى فيها المطهّر رطبًا على السطح.')
    surfaces = fields.Char(string='الأسطح المناسبة')
    food_safe = fields.Boolean(string='مسموح في مناطق الأغذية')
    ppe_note = fields.Char(string='معدّات الوقاية المطلوبة')
    hazard_note = fields.Text(string='تحذيرات')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def name_get(self):
        return [(r.id, '%s (%s)' % (r.name, r.active_ingredient or '')) for r in self]


class DisinfectRound(models.Model):
    _name = 'care.disinfect.round'
    _description = 'جولة تعقيم'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'done_at desc, id desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True,
                                  tracking=True, index=True)
    location_id = fields.Many2one('care.cafm.location', string='الموقع', tracking=True)
    round_type = fields.Selection([
        ('routine', 'تعقيم دوري'), ('terminal', 'تعقيم نهائي بعد خروج مريض'),
        ('outbreak', 'استجابة لحالة عدوى'), ('preventive', 'وقائي مجدول'),
    ], string='نوع الجولة', default='routine', required=True, tracking=True)
    method = fields.Selection([
        ('wipe', 'مسح بالمناديل'), ('spray', 'رشّ'), ('fog', 'تضبيب'),
        ('uv', 'أشعة فوق بنفسجية'), ('electrostatic', 'رشّ كهروستاتيكي'),
    ], string='الطريقة', default='wipe', required=True, tracking=True)
    done_at = fields.Datetime(string='وقت التنفيذ', default=fields.Datetime.now,
                              required=True, index=True, tracking=True)
    done_by = fields.Many2one('hr.employee', string='المنفّذ', tracking=True)
    product_id = fields.Many2one('care.disinfect.product', string='المطهّر المستخدم',
                                 required=True, tracking=True)
    dilution_used = fields.Char(string='التخفيف المستخدم')
    contact_minutes = fields.Integer(string='زمن التلامس المُطبَّق (دقيقة)', required=True,
                                     default=1, tracking=True)
    required_minutes = fields.Integer(related='product_id.contact_minutes',
                                      string='المطلوب (دقيقة)')
    contact_ok = fields.Boolean(string='زمن التلامس مُحترَم', compute='_compute_contact',
                                store=True)

    # the surfaces that actually matter
    hit_handles = fields.Boolean(string='المقابض والأزرار')
    hit_rails = fields.Boolean(string='الحواف والدرابزين')
    hit_switches = fields.Boolean(string='المفاتيح واللوحات')
    hit_equipment = fields.Boolean(string='الأجهزة غير الحرجة')
    hit_sanitary = fields.Boolean(string='الأطقم الصحية')
    fresh_cloth = fields.Boolean(string='منشفة نظيفة لكل غرفة', default=True,
                                 help='إعادة استخدام المنشفة تنقل التلوّث بدل إزالته.')
    ventilated = fields.Boolean(string='تمّت التهوية قبل إعادة التشغيل')

    atp_tested = fields.Boolean(string='أُخذ مسح ATP')
    atp_reading = fields.Integer(string='قراءة ATP (RLU)',
                                 help='أقل من 100 وحدة يُعدّ سطحًا نظيفًا في الأوساط الطبية.')
    atp_pass = fields.Boolean(string='اجتاز مسح ATP', compute='_compute_atp', store=True)

    state = fields.Selection([
        ('draft', 'مسودة'), ('done', 'منفّذة'), ('rework', 'تحتاج إعادة'),
    ], string='الحالة', default='draft', required=True, tracking=True)
    note = fields.Text(string='ملاحظات')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    SURFACES = ['hit_handles', 'hit_rails', 'hit_switches', 'hit_equipment', 'hit_sanitary']

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.disinfect.round') or '/'
        return super().create(vals_list)

    @api.depends('contact_minutes', 'product_id.contact_minutes')
    def _compute_contact(self):
        for r in self:
            need = r.product_id.contact_minutes or 0
            r.contact_ok = bool(r.contact_minutes and r.contact_minutes >= need)

    @api.depends('atp_tested', 'atp_reading')
    def _compute_atp(self):
        for r in self:
            r.atp_pass = bool(r.atp_tested and r.atp_reading and r.atp_reading < 100)

    @api.onchange('product_id')
    def _onchange_product(self):
        """Default the dwell time to what the product actually requires, so the
        common case is right and a shorter time is a deliberate entry."""
        for r in self:
            if r.product_id:
                r.contact_minutes = r.product_id.contact_minutes
                r.dilution_used = r.product_id.dilution

    def action_done(self):
        for r in self:
            if not any(r[f] for f in self.SURFACES):
                raise UserError(_('حدّد الأسطح التي جرى تعقيمها.'))
            if not r.contact_ok:
                # not a hard block — it is a fact about this round that must
                # survive into the record instead of being argued about later
                r.state = 'rework'
                r.message_post(body=_(
                    '⚠️ زمن التلامس المُطبَّق %s دقيقة أقل من المطلوب %s — الجولة تحتاج إعادة.')
                    % (r.contact_minutes, r.required_minutes))
                continue
            if r.atp_tested and not r.atp_pass:
                r.state = 'rework'
                r.message_post(body=_('⚠️ مسح ATP %s RLU فوق الحد — الجولة تحتاج إعادة.')
                               % r.atp_reading)
                continue
            r.state = 'done'

    def action_reset(self):
        self.write({'state': 'draft'})
