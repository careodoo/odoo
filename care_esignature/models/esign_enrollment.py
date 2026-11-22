# -*- coding: utf-8 -*-
# سجلّ «اعتماد التوقيع الإلكتروني» للموظف: طلب ← اعتماد ← توقيع النموذج ورفعه ← تفعيل،
# مع إمكانية التعطيل/التفعيل. محميّ: لا يُدار إلا من مدير منظومة التواقيع.
import random
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CareEsignEnrollment(models.Model):
    _name = 'care.esign.enrollment'
    _description = 'اعتماد التوقيع الإلكتروني للموظف'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(string='رقم الاعتماد', default='/', copy=False, readonly=True,
                       index=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='الموظّف', required=True,
                                  tracking=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='المستخدم', related='employee_id.user_id',
                              store=True, readonly=True)
    department_id = fields.Many2one('hr.department', string='القسم / المشروع',
                                    related='employee_id.department_id', store=True, readonly=True)
    job_id = fields.Many2one('hr.job', string='المسمّى الوظيفي',
                             related='employee_id.job_id', store=True, readonly=True)
    identification_id = fields.Char(string='الرقم الوظيفي',
                                    related='employee_id.identification_id', readonly=True)

    state = fields.Selection([
        ('draft', 'طلب'),
        ('to_approve', 'بانتظار الاعتماد'),
        ('approved', 'معتمد — بانتظار توقيع الموظف'),
        ('active', 'فعّال'),
        ('disabled', 'معطّل'),
        ('revoked', 'ملغى (إلغاء نهائي)'),
        ('rejected', 'مرفوض'),
    ], string='الحالة', default='draft', required=True, tracking=True, copy=False)

    request_date = fields.Date(string='تاريخ الطلب', default=fields.Date.context_today, tracking=True)
    requested_by = fields.Many2one('res.users', string='مُقدّم الطلب',
                                   default=lambda s: s.env.user, readonly=True)
    approved_by = fields.Many2one('res.users', string='اعتمده', readonly=True, copy=False)
    approved_date = fields.Date(string='تاريخ الاعتماد', readonly=True, copy=False)

    signed_form = fields.Binary(string='صورة اعتماد التوقيع بعد توقيع الموظف عليها', attachment=True, copy=False,
                                help='تُرفع صورة/ملف نموذج الاعتماد بعد توقيع الموظف عليه — يصبح التوقيع فعّالاً بعد رفعها.')
    signed_form_filename = fields.Char(string='اسم ملف النموذج', copy=False)
    # صورة التوقيع الإلكتروني للموظف — تُقرأ مباشرة من ملف الموظف (للعرض فقط)
    employee_signature = fields.Binary(string='التوقيع الإلكتروني للموظف', readonly=True,
                                       compute='_compute_employee_signature')

    @api.depends('user_id', 'user_id.esign_signature')
    def _compute_employee_signature(self):
        """قراءة توقيع الموظف بـ sudo حتى يظهر مهما كانت شركة المرفق مختلفة عن شركة الاعتماد."""
        for rec in self:
            rec.employee_signature = (rec.user_id.sudo().esign_signature
                                      if rec.user_id else False)

    effective_date = fields.Date(string='تاريخ التفعيل', readonly=True, copy=False)
    disabled_by = fields.Many2one('res.users', string='عطّله', readonly=True, copy=False)
    disabled_date = fields.Date(string='تاريخ التعطيل', readonly=True, copy=False)
    disable_reason = fields.Text(string='سبب التعطيل', copy=False)
    # الإلغاء النهائي (طلب إلغاء اعتماد التوقيع)
    revocation_date = fields.Date(string='تاريخ الإلغاء', readonly=True, copy=False)
    revoked_by = fields.Many2one('res.users', string='ألغاه', readonly=True, copy=False)
    revocation_reason = fields.Text(string='سبب الإلغاء', copy=False)
    revocation_serial = fields.Char(string='الرقم التسلسلي للإلغاء', readonly=True, copy=False, index=True)

    policy_version = fields.Char(string='إصدار السياسة', default='v1.0', readonly=True)
    serial = fields.Char(string='الرقم التسلسلي', readonly=True, copy=False, index=True)
    note = fields.Text(string='ملاحظات')
    company_id = fields.Many2one('res.company', string='الشركة',
                                 default=lambda s: s.env.company)

    _sql_constraints = [
        ('uniq_serial', 'unique(serial)', 'الرقم التسلسلي للاعتماد يجب أن يكون فريدًا.'),
    ]

    # ------- الإنشاء + القيد (اعتماد واحد قائم لكل موظف) -------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'care.esign.enrollment') or '/'
            emp_id = vals.get('employee_id')
            if emp_id:
                open_any = self.search([
                    ('employee_id', '=', emp_id),
                    ('state', 'not in', ('rejected', 'disabled'))], limit=1)
                if open_any:
                    emp = self.env['hr.employee'].browse(emp_id)
                    raise UserError(_(
                        'يوجد اعتماد توقيع إلكتروني قائم لهذا الموظف (%s): %s. '
                        'لا يمكن إنشاء اعتماد جديد قبل رفض/تعطيل السابق.'
                    ) % (emp.name, open_any.name))
        return super().create(vals_list)

    # ------- توليد السيريال ENR-YYYYMMDD-HHMM-EMPID-HEX4 -------
    def _gen_serial(self):
        self.ensure_one()
        dt = fields.Datetime.now()
        h = ''.join(random.choice('0123456789ABCDEF') for _ in range(4))
        return 'ENR-%s-%s-%05d-%s' % (
            dt.strftime('%Y%m%d'), dt.strftime('%H%M'), int(self.employee_id.id or 0), h)

    def _assign_serial(self):
        for rec in self:
            if not rec.serial:
                for _try in range(8):
                    s = rec._gen_serial()
                    if not self.sudo().search_count([('serial', '=', s)]):
                        rec.serial = s
                        break

    # ------- ضبط حالة تعطيل التوقيع على المستخدم (بأمان) -------
    def _set_user_disabled(self, disabled):
        for rec in self:
            user = rec.user_id
            if user:
                user.sudo().write({'esign_disabled': bool(disabled)})

    # ------- الأفعال -------
    def action_submit(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('لا يمكن تقديم إلا طلبًا في حالة «طلب».'))
            rec.state = 'to_approve'
            rec.message_post(body=_('تم تقديم طلب اعتماد التوقيع الإلكتروني للاعتماد.'))

    def action_approve(self):
        for rec in self:
            if rec.state != 'to_approve':
                raise UserError(_('لا يمكن اعتماد إلا طلبًا بانتظار الاعتماد.'))
            rec._assign_serial()
            rec.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approved_date': fields.Date.context_today(self),
            })
            rec.message_post(body=_('تم اعتماد الطلب — بانتظار توقيع الموظف ورفع النموذج.'))

    def action_reject(self):
        for rec in self:
            if rec.state in ('active', 'disabled'):
                raise UserError(_('لا يمكن رفض اعتماد فعّال أو معطّل.'))
            rec._clear_signatures()
            rec.state = 'rejected'
            rec.message_post(body=_('تم رفض طلب اعتماد التوقيع الإلكتروني، وحُذفت التوقيعات من النموذج.'))

    def _clear_signatures(self):
        """حذف كل التوقيعات من النموذج (المرفوع + المركزي) — عند الإلغاء/الإرجاع لمسودة."""
        for rec in self:
            rec.write({'signed_form': False, 'signed_form_filename': False})
            self.env['care.esignature'].sudo().clear_for(rec._name, rec.id)

    def action_reset_to_draft(self):
        """إرجاع الطلب إلى «مسودة» مع حذف التوقيعات والاعتمادات السابقة لإعادة المعالجة."""
        for rec in self:
            if rec.state == 'active':
                raise UserError(_('لا يمكن إرجاع اعتماد فعّال إلى مسودة؛ عطّله أو ألغِه أولًا.'))
            rec._clear_signatures()
            rec.write({
                'state': 'draft',
                'approved_by': False,
                'approved_date': False,
                'effective_date': False,
                'disabled_by': False,
                'disabled_date': False,
            })
            rec.message_post(body=_('أُعيد الطلب إلى «مسودة» وحُذفت التوقيعات السابقة.'))

    def action_activate(self):
        for rec in self:
            if rec.state != 'approved':
                raise UserError(_('لا يمكن التفعيل إلا لطلب معتمد.'))
            if not rec.signed_form:
                raise UserError(_('يجب رفع النموذج الموقّع من الموظف قبل التفعيل.'))
            rec.write({
                'state': 'active',
                'effective_date': fields.Date.context_today(self),
            })
            rec._set_user_disabled(False)
            rec.message_post(body=_('أصبح التوقيع الإلكتروني فعّالاً.'))

    def action_disable(self):
        for rec in self:
            if rec.state not in ('active', 'approved'):
                raise UserError(_('لا يمكن تعطيل إلا اعتماد فعّال.'))
            rec.write({
                'state': 'disabled',
                'disabled_by': self.env.user.id,
                'disabled_date': fields.Date.context_today(self),
            })
            rec._set_user_disabled(True)
            rec.message_post(body=_('تم تعطيل التوقيع الإلكتروني لهذا الموظف.'))

    def action_enable(self):
        for rec in self:
            if rec.state != 'disabled':
                raise UserError(_('لا يمكن إعادة التفعيل إلا لاعتماد معطّل.'))
            rec.write({'state': 'active'})
            rec._set_user_disabled(False)
            rec.message_post(body=_('تمت إعادة تفعيل التوقيع الإلكتروني.'))

    # ------- طلب إلغاء اعتماد التوقيع (إلغاء نهائي + نموذج رسمي) -------
    def _gen_revocation_serial(self):
        self.ensure_one()
        import random
        dt = fields.Datetime.now()
        h = ''.join(random.choice('0123456789ABCDEF') for _ in range(4))
        base = (self.name or 'ESE').replace('/', '')
        return 'REV-%s-%s-%s-%s' % (base, dt.strftime('%Y%m%d'), dt.strftime('%H%M'), h)

    def action_revoke(self):
        """إلغاء نهائي لاعتماد التوقيع — يصدر نموذج إلغاء رسميًّا ويعطّل التوقيع."""
        for rec in self:
            if rec.state == 'revoked':
                raise UserError(_('هذا الاعتماد ملغى بالفعل.'))
            if rec.state in ('draft', 'to_approve', 'rejected'):
                raise UserError(_('لا يُلغى إلا اعتماد معتمد أو فعّال أو معطّل.'))
            rec.write({
                'state': 'revoked',
                'revocation_date': fields.Date.context_today(rec),
                'revoked_by': self.env.user.id,
            })
            if not rec.revocation_serial:
                rec.revocation_serial = rec._gen_revocation_serial()
            rec._set_user_disabled(True)
            rec.message_post(body=_(
                'تم إلغاء اعتماد التوقيع الإلكتروني نهائيًّا اعتبارًا من %s — أي استخدام بعد هذا التاريخ غير صحيح.'
            ) % rec.revocation_date)
        return True

    def revocation_qr_datauri(self):
        """QR نموذج الإلغاء — يرمّز سيريال الإلغاء + رقم الاعتماد + تاريخ الإلغاء."""
        self.ensure_one()
        if not self.revocation_serial:
            return ''
        try:
            import base64
            val = 'ESIGN-REVOKED|%s|%s|%s' % (self.revocation_serial, self.name or '', self.revocation_date or '')
            png = self.env['ir.actions.report'].sudo().barcode('QR', val, width=120, height=120)
            if isinstance(png, str):
                png = png.encode('latin-1', 'ignore')
            return 'data:image/png;base64,' + base64.b64encode(png).decode()
        except Exception:
            return ''

    def action_print_revocation(self):
        self.ensure_one()
        return self.env.ref('care_esignature.action_report_esign_revocation').report_action(self)

    # ------- فتح تقرير النموذج -------
    def action_print_form(self):
        self.ensure_one()
        return self.env.ref('care_esignature.action_report_esign_enrollment').report_action(self)

    # ------- بنود السياسة ثنائية اللغة (للتقرير) -------
    @api.model
    def _policy_clauses(self):
        """بنود سياسة وشروط استخدام التوقيع الإلكتروني — عربي + إنجليزي (مطابقة للموكاب)."""
        return [
            ('التعريف والحجّية',
             'التوقيع الإلكتروني المعتمد في نظام شركة الرعاية لمقاولات تنظيف المباني والمدن بديلٌ مُلزِمٌ عن التوقيع اليدوي على المستندات والاعتمادات داخل النظام، وله الأثر القانوني ذاته وفق الأنظمة المعمول بها في دولة الكويت.',
             'Definition & legal effect',
             "The electronic signature adopted in CARE's system is a binding substitute for the handwritten signature on documents and approvals within the system, with the same legal effect under the laws in force in the State of Kuwait."),
            ('الموافقة الصريحة',
             'يُقِرّ الموظف بموافقته الصريحة على إنشاء توقيعٍ إلكترونيٍّ خاصٍّ به واستخدامه لتوثيق موافقاته واعتماداته على المستندات الصادرة عبر النظام.',
             'Express consent',
             'The employee expressly consents to the creation of a personal electronic signature and its use to authenticate their approvals on documents issued through the system.'),
            ('الخصوصية والمسؤولية',
             'التوقيع الإلكتروني وبيانات الدخول شخصيةٌ وسرّية، ويتحمّل الموظف كامل المسؤولية عن أي استخدامٍ يتمّ عبر حسابه، ولا يجوز تفويض الغير باستخدامه.',
             'Confidentiality & responsibility',
             'The electronic signature and login credentials are personal and confidential; the employee bears full responsibility for any use made through their account and may not delegate its use to others.'),
            ('نطاق الاستخدام',
             'يُستخدم التوقيع حصرًا داخل أنظمة الشركة وللأغراض الوظيفية المصرّح بها (الاعتمادات والطلبات والمستندات الرسمية) دون غيرها.',
             'Scope of use',
             "The signature is used solely within the Company's systems and for authorized work purposes (approvals, requests and official documents)."),
            ('القصر على الإجراءات الإدارية',
             'يُخصَّص التوقيع الإلكتروني للإجراءات الإدارية والموافقات داخل النظام فقط، ولا يجوز اعتماده في استلام المستحقات المالية أو المرتبات الخاصة بالموظف.',
             'Administrative use only',
             "The electronic signature is designated solely for administrative procedures and approvals within the system; it may not be relied upon for the receipt of the employee's financial dues or salaries."),
            ('الاستخدام بإذن والتوقيع المزدوج',
             'لا يجوز للشركة استخدام التوقيع الإلكتروني للموظف دون إذنه، وللإدارة العليا أن تطلب توقيعًا يدويًّا (حقيقيًّا) إلى جانب التوقيع الإلكتروني متى رأت ذلك مناسبًا.',
             'Use by consent & dual signature',
             "The Company may not use the employee's electronic signature without their consent; senior management may require a handwritten (wet-ink) signature alongside the electronic signature whenever deemed appropriate."),
            ('عدم الإنكار والتتبّع',
             'يحمل كلّ توقيعٍ رقمًا تسلسليًّا فريدًا وختمًا زمنيًّا ورمز تحقّق (QR)، ولا يجوز للموظف إنكار ما وقّعه إلكترونيًّا عبر حسابه.',
             'Non-repudiation & traceability',
             'Every signature carries a unique serial number, a timestamp and a QR verification code; the employee may not deny what they have signed electronically through their account.'),
            ('الإبلاغ الفوري',
             'يلتزم الموظف بإبلاغ إدارة النظام فورًا عن أي استخدامٍ غير مصرّحٍ به أو اشتباهٍ باختراق حسابه.',
             'Immediate reporting',
             'The employee undertakes to notify system administration immediately of any unauthorized use or suspected compromise of their account.'),
            ('شرط التفعيل',
             'لا يصبح التوقيع الإلكتروني فعّالًا إلا بعد اعتماد الطلب وتوقيع الموظف على هذا النموذج ورفعه موقّعًا إلى النظام.',
             'Activation condition',
             'The electronic signature becomes effective only after the request is approved, the employee signs this form, and the signed form is uploaded to the system.'),
            ('الإيقاف والإلغاء',
             'يحقّ للشركة تعطيل أو إلغاء التوقيع الإلكتروني لأي موظفٍ في أي وقت، كما يُلغى تلقائيًّا عند انتهاء العلاقة الوظيفية.',
             'Suspension & revocation',
             "The Company reserves the right to disable or revoke any employee's electronic signature at any time; it is also revoked automatically upon termination of employment."),
            ('السريان',
             'تسري هذه الموافقة من تاريخ التفعيل وتبقى نافذةً حتى إلغائها كتابةً أو انتهاء الخدمة.',
             'Validity',
             'This consent takes effect from the activation date and remains in force until revoked in writing or employment ends.'),
            ('الإقرار',
             'بتوقيعي أدناه أُقِرّ بأنّني قرأتُ هذه السياسة وفهمتُ بنودها وأوافق على الالتزام بها كاملةً.',
             'Acknowledgement',
             'By signing below, I acknowledge that I have read this policy, understood its provisions, and agree to comply with it in full.'),
        ]

    # ------- ديمو آمن (بلا refs صلبة) -------
    @api.model
    def _create_demo_enrollments(self):
        """ينشئ سجلّات ديمو بحالات مختلفة على أوائل الموظفين — آمن: يتخطّى إن لا موظفين أو موجودة."""
        emps = self.env['hr.employee'].search([('user_id', '!=', False)], limit=3)
        if not emps:
            emps = self.env['hr.employee'].search([], limit=3)
        states = ['active', 'approved', 'disabled']
        for i, emp in enumerate(emps):
            if self.search_count([('employee_id', '=', emp.id)]):
                continue
            try:
                rec = self.create({'employee_id': emp.id})
                st = states[i % len(states)]
                if st == 'approved':
                    rec.action_submit(); rec.action_approve()
                elif st == 'active':
                    rec.action_submit(); rec.action_approve()
                    rec.write({'signed_form': b'ZGVtbw==', 'signed_form_filename': 'demo_signed.pdf'})
                    rec.action_activate()
                elif st == 'disabled':
                    rec.action_submit(); rec.action_approve()
                    rec.write({'signed_form': b'ZGVtbw==', 'signed_form_filename': 'demo_signed.pdf'})
                    rec.action_activate(); rec.action_disable()
            except Exception:
                continue
        return True
