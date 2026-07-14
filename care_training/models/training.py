# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class CareTrainingCourse(models.Model):
    _name = 'care.training.course'
    _description = 'Training Course'
    _order = 'name'

    name = fields.Char(string='الدورة', required=True, translate=True)
    code = fields.Char(string='الرمز')
    category = fields.Selection([
        ('safety', 'سلامة (HSE)'), ('skill', 'مهارية'), ('induction', 'تعريفية/تأهيل'),
        ('compliance', 'امتثال/قانوني'), ('soft', 'مهارات شخصية'),
    ], string='التصنيف', default='skill', required=True)
    duration_hours = fields.Float(string='عدد الساعات')
    is_mandatory = fields.Boolean(string='إلزامية')
    validity_months = fields.Integer(string='صلاحية الشهادة (شهور)',
                                     help='0 = شهادة دائمة بلا انتهاء.')
    description = fields.Text(string='الوصف')
    active = fields.Boolean(default=True)
    session_count = fields.Integer(compute='_compute_counts')

    def _compute_counts(self):
        Session = self.env['care.training.session']
        for c in self:
            c.session_count = Session.search_count([('course_id', '=', c.id)])


class CareTrainingSession(models.Model):
    _name = 'care.training.session'
    _description = 'Training Session'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    course_id = fields.Many2one('care.training.course', string='الدورة', required=True, tracking=True)
    category = fields.Selection(related='course_id.category', store=True)
    trainer_id = fields.Many2one('res.users', string='المدرّب', tracking=True)
    trainer_name = fields.Char(string='مدرّب خارجي')
    date = fields.Datetime(string='تاريخ البداية', default=fields.Datetime.now, required=True, tracking=True)
    end_date = fields.Datetime(string='تاريخ النهاية')
    location = fields.Char(string='المكان')
    department_id = fields.Many2one('hr.department', string='القسم/المشروع')
    capacity = fields.Integer(string='السعة')
    state = fields.Selection([
        ('planned', 'مخطط'), ('confirmed', 'مؤكّد'), ('ongoing', 'جارٍ'),
        ('done', 'منتهٍ'), ('cancelled', 'ملغى'),
    ], default='planned', required=True, tracking=True)
    enrollment_ids = fields.One2many('care.training.enrollment', 'session_id', string='المتدربون')
    enrolled_count = fields.Integer(compute='_compute_counts', store=True)
    passed_count = fields.Integer(compute='_compute_counts', store=True)
    note = fields.Text()
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('enrollment_ids', 'enrollment_ids.result')
    def _compute_counts(self):
        for s in self:
            s.enrolled_count = len(s.enrollment_ids)
            s.passed_count = len(s.enrollment_ids.filtered(lambda e: e.result == 'pass'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.training.session') or '/'
        return super().create(vals_list)

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_start(self):
        self.write({'state': 'ongoing'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_enroll_department(self):
        """Enroll every active employee of the chosen department."""
        for s in self:
            if not s.department_id:
                raise UserError(_('اختر القسم/المشروع أولاً.'))
            existing = s.enrollment_ids.mapped('employee_id')
            emps = self.env['hr.employee'].search([('department_id', '=', s.department_id.id)])
            vals = [(0, 0, {'employee_id': e.id}) for e in emps if e not in existing]
            if vals:
                s.enrollment_ids = vals


class CareTrainingEnrollment(models.Model):
    _name = 'care.training.enrollment'
    _description = 'Training Enrollment'
    _order = 'employee_id, id'

    session_id = fields.Many2one('care.training.session', required=True, ondelete='cascade', index=True)
    employee_id = fields.Many2one('hr.employee', string='المتدرب', required=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True, string='القسم')
    course_id = fields.Many2one(related='session_id.course_id', store=True, string='الدورة')
    session_date = fields.Datetime(related='session_id.date', store=True, string='تاريخ الدورة')
    attended = fields.Boolean(string='حضر')
    result = fields.Selection([
        ('pending', 'قيد الانتظار'), ('pass', 'ناجح'), ('fail', 'راسب'),
    ], string='النتيجة', default='pending', required=True)
    score = fields.Float(string='الدرجة %')
    certificate_no = fields.Char(string='رقم الشهادة')
    certificate_expiry = fields.Date(string='انتهاء الشهادة', compute='_compute_expiry', store=True)
    cert_state = fields.Selection([
        ('none', 'لا شهادة'), ('valid', 'سارية'), ('expiring', 'تقترب'), ('expired', 'منتهية'),
    ], compute='_compute_expiry', store=True, string='حالة الشهادة')
    note = fields.Char()

    @api.depends('result', 'session_id.date', 'course_id.validity_months')
    def _compute_expiry(self):
        today = fields.Date.today()
        for e in self:
            if e.result == 'pass' and e.session_id.date and e.course_id.validity_months:
                exp = fields.Date.to_date(e.session_id.date) + relativedelta(months=e.course_id.validity_months)
                e.certificate_expiry = exp
                days = (exp - today).days
                e.cert_state = 'expired' if exp < today else ('expiring' if days <= 60 else 'valid')
            elif e.result == 'pass':
                e.certificate_expiry = False
                e.cert_state = 'valid'
            else:
                e.certificate_expiry = False
                e.cert_state = 'none'
