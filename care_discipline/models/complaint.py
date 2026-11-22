# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class CareComplaintCategory(models.Model):
    _name = 'care.complaint.category'
    _description = 'نوع المخالفة'
    _order = 'sequence, id'

    name = fields.Char(string='النوع', required=True, translate=True)
    name_en = fields.Char(string='Name (EN)')
    sequence = fields.Integer(default=10)
    default_severity = fields.Selection(
        [('low', 'بسيطة'), ('medium', 'متوسّطة'), ('high', 'جسيمة')],
        string='الخطورة الافتراضية', default='medium')
    # الجزاء المقترح لأول مخالفة (يُستخدم في التدرّج)
    suggested_penalty = fields.Selection(
        [('warning', 'إنذار'), ('deduction', 'خصم'),
         ('suspension', 'إيقاف'), ('termination', 'إنهاء خدمة')],
        string='الجزاء المقترح', default='warning')
    free_text = fields.Boolean(string='نوع حرّ («أخرى» — يُكتب يدويًّا)',
                               help='عند اختيار هذا النوع يُطلب من مُقدّم الشكوى كتابة نوع المخالفة.')
    active = fields.Boolean(default=True)


class HrEmployeeDiscipline(models.Model):
    _inherit = 'hr.employee'

    discipline_count = fields.Integer(string='شكاوى تأديبية', compute='_compute_discipline_count')

    def _compute_discipline_count(self):
        data = self.env['care.complaint'].sudo()._read_group(
            [('employee_id', 'in', self.ids)], ['employee_id'], ['__count'])
        mapped = {emp.id: count for emp, count in data}
        for e in self:
            e.discipline_count = mapped.get(e.id, 0)


class CareComplaint(models.Model):
    _name = 'care.complaint'
    _description = 'شكوى / إجراء تأديبي'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(string='الرقم', required=True, copy=False, readonly=True,
                       default=lambda s: _('New'), index=True)
    # ===== الأطراف =====
    employee_id = fields.Many2one('hr.employee', string='الموظف المُشتكى عليه',
                                  required=True, tracking=True, index=True)
    department_id = fields.Many2one(related='employee_id.department_id',
                                    string='القسم / المشروع', store=True)
    complainant_id = fields.Many2one('res.users', string='مُقدّم الشكوى',
                                     default=lambda s: s.env.user, readonly=True, tracking=True)
    manager_id = fields.Many2one('res.users', string='المدير المباشر (المعتمِد)', tracking=True)
    hr_user_id = fields.Many2one('res.users', string='الموارد البشرية', readonly=True, copy=False)
    legal_user_id = fields.Many2one('res.users', string='المستشار القانوني', readonly=True, copy=False)

    # ===== تفاصيل الواقعة =====
    category_other = fields.Char(string='نوع المخالفة (أخرى — حدّد)',
                                 help='يُكتب نوع المخالفة يدويًّا عند اختيار نوع «أخرى».')
    category_is_free = fields.Boolean(related='category_id.free_text')
    category_id = fields.Many2one('care.complaint.category', string='نوع المخالفة',
                                  required=True, tracking=True)
    severity = fields.Selection(
        [('low', 'بسيطة'), ('medium', 'متوسّطة'), ('high', 'جسيمة')],
        string='درجة الخطورة', default='medium', required=True, tracking=True)
    incident_date = fields.Date(string='تاريخ الواقعة', default=fields.Date.context_today,
                                required=True, tracking=True)
    description = fields.Text(string='وصف الواقعة', required=True)
    attachment_ids = fields.Many2many('ir.attachment', string='الأدلة والمرفقات')
    witnesses = fields.Char(string='الشهود')
    complainant_ack = fields.Boolean(string='إقرار مُقدّم الشكوى بصحّة البيانات')

    # ===== حق الدفاع / التحقيق =====
    defense_statement = fields.Text(string='أقوال / دفاع العامل', tracking=True)
    defense_date = fields.Date(string='تاريخ سماع الأقوال', readonly=True, copy=False)
    investigation_notes = fields.Text(string='محضر التحقيق')

    # ===== القرار القانوني =====
    penalty_type = fields.Selection(
        [('warning', 'إنذار كتابي'), ('deduction', 'خصم من الأجر'),
         ('suspension', 'الإيقاف عن العمل'), ('termination', 'إنهاء الخدمة'),
         ('none', 'لا جزاء — غير مثبتة')],
        string='الجزاء المُقرَّر', tracking=True)
    law_article_id = fields.Many2one('care.labor.law.article', string='السند القانوني')
    deduction_days = fields.Float(string='أيام الخصم')
    legal_reasoning = fields.Text(string='حيثيات القرار')
    prior_count = fields.Integer(string='مخالفات سابقة (هذا العام)',
                                 compute='_compute_prior', store=False)

    # ===== التطبيق والربط =====
    penalty_id = fields.Many2one('care.penalty', string='سجل الخصم', readonly=True, copy=False)
    suspension_id = fields.Many2one('care.suspension.request', string='سجل الإيقاف', readonly=True, copy=False)
    applied_date = fields.Date(string='تاريخ التطبيق', readonly=True, copy=False)

    # ===== الحالة =====
    state = fields.Selection([
        ('draft', 'مسوّدة'),
        ('submitted', 'بانتظار المدير المباشر'),
        ('manager_approved', 'بانتظار الموارد البشرية'),
        ('hr_review', 'تحقيق (الموارد البشرية)'),
        ('legal_review', 'بانتظار الإدارة القانونية'),
        ('penalty_decided', 'بانتظار تطبيق الجزاء'),
        ('applied', 'طُبّق الجزاء'),
        ('closed', 'مُغلقة'),
        ('rejected', 'مرفوضة'),
    ], string='الحالة', default='draft', tracking=True, copy=False, index=True)
    reject_reason = fields.Char(string='سبب الرفض', readonly=True, copy=False)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    # ---------- helpers: الإعدادات (الخيارات) ----------
    def _opt(self, field):
        """قيمة خيار على مستوى الشركة (الأفكار كخيارات تُفعَّل/تُعطَّل)."""
        return getattr(self.company_id or self.env.company, field, False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('care.complaint') or _('New')
        return super().create(vals_list)

    @api.onchange('category_id')
    def _onchange_category(self):
        if self.category_id and self.category_id.default_severity:
            self.severity = self.category_id.default_severity

    @api.constrains('category_id', 'category_other')
    def _check_category_other(self):
        for r in self:
            if r.category_id and r.category_id.free_text and not (r.category_other or '').strip():
                raise ValidationError(_('اخترت نوع «أخرى» — فاكتب نوع المخالفة في خانة «نوع المخالفة (أخرى)».'))

    def category_label(self):
        """الاسم الظاهر للنوع: النص الحرّ إن كان النوع «أخرى»، وإلا اسم الفئة."""
        self.ensure_one()
        if self.category_id and self.category_id.free_text and self.category_other:
            return self.category_other
        return self.category_id.name if self.category_id else ''

    @api.depends('employee_id')
    def _compute_prior(self):
        for r in self:
            n = 0
            if r.employee_id:
                yr = (r.incident_date or fields.Date.context_today(r)).year
                n = self.sudo().search_count([
                    ('employee_id', '=', r.employee_id.id),
                    ('state', 'in', ('applied', 'closed')),
                    ('penalty_type', 'not in', ('none', False)),
                    ('incident_date', '>=', '%s-01-01' % yr)])
            r.prior_count = n

    def _esign(self, role):
        if self._opt('disc_esign'):
            try:
                self.env['care.esignature'].sudo().esign_sign(self._name, self.id, role=role)
            except Exception:
                pass

    def _notify(self, users, body):
        try:
            if users:
                self.message_post(body=body, partner_ids=users.mapped('partner_id').ids,
                                  subtype_xmlid='mail.mt_comment')
        except Exception:
            pass

    def _group_users(self, xmlid):
        grp = self.env.ref(xmlid, raise_if_not_found=False)
        return grp.users if grp else self.env['res.users']

    # ---------- سير العمل ----------
    def action_submit(self):
        for r in self:
            if r.state != 'draft':
                raise UserError(_('تُقدَّم الشكوى من المسوّدة فقط.'))
            if r._opt('disc_false_guard') and not r.complainant_ack:
                raise UserError(_('يجب الإقرار بصحّة البيانات (حماية من الشكوى الكيدية).'))
            if r._opt('disc_prescription'):
                days = r.company_id.disc_prescription_days or 90
                if r.incident_date and (fields.Date.context_today(r) - r.incident_date).days > days:
                    raise UserError(_('مضى على الواقعة أكثر من مدّة التقادم (%s يومًا) — لا يجوز الجزاء.') % days)
            if not r.manager_id:
                r.manager_id = (r.employee_id.parent_id.user_id
                                or r.env.user).id if r.employee_id.parent_id else r.env.user.id
            r.state = 'submitted'
            r._esign('مُقدّم الشكوى')
            r._notify(r.manager_id, _('📝 شكوى جديدة %s بانتظار اعتمادك.') % r.name)

    def action_manager_approve(self):
        for r in self:
            if r.state != 'submitted':
                raise UserError(_('تُعتمد الشكوى المُقدَّمة فقط.'))
            # الاعتماد خاص بالمدير المباشر المحدّد (أو مدير النظام)
            if r.manager_id and r.env.user != r.manager_id \
                    and not r.env.user.has_group('base.group_system') \
                    and not r.env.user.has_group('care_discipline.group_discipline_hr'):
                raise UserError(_('الاعتماد خاص بالمدير المباشر المحدّد لهذه الشكوى.'))
            r.state = 'manager_approved'
            r._esign('المدير المباشر')
            hr = r._group_users('care_discipline.group_discipline_hr')
            r._notify(hr, _('✅ شكوى %s معتمَدة من المدير — بانتظار الموارد البشرية.') % r.name)

    def action_hr_take(self):
        """الموارد البشرية تستلم وتفتح التحقيق."""
        self._grp_require('care_discipline.group_discipline_hr', _('خاص بالموارد البشرية.'))
        for r in self:
            if r.state != 'manager_approved':
                raise UserError(_('تُستلم الشكوى المعتمَدة من المدير فقط.'))
            r.hr_user_id = r.env.uid
            r.state = 'hr_review'

    def action_record_defense(self):
        for r in self:
            if not r.defense_statement:
                raise UserError(_('سجّل أقوال/دفاع العامل أولًا.'))
            r.defense_date = fields.Date.context_today(r)
            r.message_post(body=_('🗣️ دُوّنت أقوال العامل.'))

    def action_hr_to_legal(self):
        self._grp_require('care_discipline.group_discipline_hr', _('خاص بالموارد البشرية.'))
        for r in self:
            if r.state != 'hr_review':
                raise UserError(_('تُحوَّل من مرحلة التحقيق فقط.'))
            if r._opt('disc_require_defense') and not r.defense_statement:
                raise UserError(_('حق الدفاع إلزامي: سجّل أقوال العامل قبل التحويل للقانونية.'))
            r.state = 'legal_review'
            r._esign('الموارد البشرية')
            legal = r._group_users('care_discipline.group_discipline_legal')
            r._notify(legal, _('⚖️ شكوى %s بانتظار قرار الإدارة القانونية.') % r.name)

    def action_legal_decide(self):
        self._grp_require('care_discipline.group_discipline_legal', _('إقرار الجزاء خاص بالإدارة القانونية.'))
        for r in self:
            if r.state != 'legal_review':
                raise UserError(_('يُقرَّر الجزاء في مرحلة المراجعة القانونية فقط.'))
            if not r.penalty_type:
                raise UserError(_('اختر الجزاء المُقرَّر.'))
            if r._opt('disc_require_law_article') and r.penalty_type != 'none' and not r.law_article_id:
                raise UserError(_('السند القانوني إلزامي: اختر المادة من قانون العمل.'))
            r.legal_user_id = r.env.uid
            r._esign('المستشار القانوني')
            if r.penalty_type == 'none':
                r.state = 'closed'
                r.message_post(body=_('✖️ الشكوى غير مثبتة — أُغلقت بلا جزاء.'))
            else:
                r.state = 'penalty_decided'
                hr = r._group_users('care_discipline.group_discipline_hr')
                r._notify(hr, _('⚖️ قرار قانوني على %s (%s) — بانتظار التطبيق.') % (
                    r.name, dict(r._fields['penalty_type'].selection).get(r.penalty_type)))

    def action_apply(self):
        """الموارد البشرية تطبّق الجزاء عبر الموديول المناسب."""
        self._grp_require('care_discipline.group_discipline_hr', _('التطبيق خاص بالموارد البشرية.'))
        for r in self:
            if r.state != 'penalty_decided':
                raise UserError(_('يُطبَّق الجزاء بعد القرار القانوني فقط.'))
            if r._opt('disc_auto_integration'):
                r._apply_integration()
            r.applied_date = fields.Date.context_today(r)
            r.state = 'applied'
            r.message_post(body=_('🔨 طُبّق الجزاء: %s.') % dict(r._fields['penalty_type'].selection).get(r.penalty_type))

    def _apply_integration(self):
        """ينشئ سجل الخصم/الإيقاف تلقائيًّا (إنهاء الخدمة = تنبيه للمسار المخصّص)."""
        self.ensure_one()
        # savepoint لكل تكامل: فشل الإنشاء يُرجَع نظيفًا دون إفساد المعاملة
        if self.penalty_type == 'deduction' and not self.penalty_id:
            try:
                with self.env.cr.savepoint():
                    Pen = self.env['care.penalty'].sudo()
                    # المبلغ = أيام الخصم × الأجر اليومي (العقد/٣٠) إن توفّر، وإلا ٠ ليُكمله HR
                    contract = self.employee_id.contract_id if 'contract_id' in self.employee_id._fields else False
                    wage = contract.wage if contract else 0.0
                    amount = round((wage / 30.0) * (self.deduction_days or 0), 3) if wage else 0.0
                    vals = {'employee_id': self.employee_id.id,
                            'date': fields.Date.context_today(self),
                            'amount': amount}
                    fmap = Pen._fields
                    if 'settle_mode' in fmap:
                        vals['settle_mode'] = 'payroll'
                    if 'policy_article' in fmap and self.law_article_id:
                        vals['policy_article'] = self.law_article_id.display_name
                    self.penalty_id = Pen.create(vals).id
                    if not amount:
                        self.penalty_id.message_post(body=_(
                            'القرار: خصم %s يوم — أدخل المبلغ (تعذّر حساب الأجر اليومي تلقائيًّا).'
                        ) % (self.deduction_days or 0))
            except Exception as e:
                self.message_post(body=_('⚠️ تعذّر إنشاء سجل الخصم تلقائيًّا (%s) — أنشئه يدويًّا.') % (str(e)[:80]))
        elif self.penalty_type == 'suspension' and not self.suspension_id:
            try:
                with self.env.cr.savepoint():
                    Susp = self.env['care.suspension.request'].sudo()
                    sv = {'employee_id': self.employee_id.id}
                    if 'note' in Susp._fields:
                        sv['note'] = _('إيقاف تأديبي — شكوى %s') % self.name
                    self.suspension_id = Susp.create(sv).id
            except Exception as e:
                self.message_post(body=_('⚠️ تعذّر إنشاء سجل الإيقاف تلقائيًّا (%s) — أنشئه يدويًّا.') % (str(e)[:80]))
        # إنهاء الخدمة: يُترك لمسار care.eos المخصّص (قرار قانوني/مالي) — إشعار فقط
        elif self.penalty_type == 'termination':
            self.message_post(body=_('🚫 قرار إنهاء خدمة — يُحوَّل لمسار نهاية الخدمة (care.eos) للاعتماد المالي.'))

    def action_close(self):
        for r in self:
            if r.state not in ('applied',):
                raise UserError(_('تُغلق الحالة بعد التطبيق.'))
            r.state = 'closed'
            r.message_post(body=_('🔒 أُغلقت الحالة وأُرشفت.'))

    def action_reject(self):
        for r in self:
            r.state = 'rejected'

    def action_print_report(self):
        self.ensure_one()
        return self.env.ref('care_discipline.action_report_complaint').report_action(self)

    def _grp_require(self, xmlid, msg):
        if not self.env.user.has_group(xmlid) and not self.env.user.has_group('base.group_system'):
            raise UserError(msg)

    @api.constrains('deduction_days')
    def _check_days(self):
        for r in self:
            if r.deduction_days and r.deduction_days < 0:
                raise ValidationError(_('أيام الخصم لا تكون سالبة.'))
