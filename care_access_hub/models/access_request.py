# -*- coding: utf-8 -*-
# «طلب إضافة صلاحية»: أي مستخدم يطلب منح صلاحية (مسمّى/مجموعة/إظهار قائمة/طوارئ) لنفسه أو لزميل،
# مؤقّتة أو دائمة. يمرّ باعتماد مدير الصلاحيات (توقيع إلكتروني) ثم يُطبَّق تلقائيًّا، ويُسحب تلقائيًّا بانتهاء المدّة.
# مدمج في مركز الموافقات، ويظهر في صفحة الملف الشخصي (خدمة ذاتية).
from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError, ValidationError


class CareAccessRequest(models.Model):
    _name = 'care.access.request'
    _description = 'طلب إضافة صلاحية'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='المرجع', default='New', copy=False, readonly=True, index=True, tracking=True)
    requester_id = fields.Many2one('res.users', string='مُقدّم الطلب', required=True,
                                   default=lambda s: s.env.user, readonly=True, tracking=True)
    user_id = fields.Many2one('res.users', string='المستخدم المستهدف', required=True,
                              domain="[('id', 'in', allowed_user_ids)]", tracking=True,
                              help='المستخدم الذي ستُمنح له الصلاحية (أنت أو أحد موظفيك فقط).')
    # القائمة المسموح بها: مُقدّم الطلب نفسه + موظفوه (org-chart + عمّال مشاريعه)
    allowed_user_ids = fields.Many2many('res.users', 'care_access_req_allowed_rel', 'req_id', 'user_id',
                                        compute='_compute_allowed_users', string='المستخدمون المسموح بهم')
    # مستوى الوصول المطلوب
    access_level = fields.Selection([('write', 'قراءة وكتابة'), ('read', 'قراءة فقط')],
                                    string='مستوى الوصول', default='write', required=True)
    employee_id = fields.Many2one('hr.employee', related='user_id.employee_id', string='الموظف', store=True)
    department_id = fields.Many2one(related='user_id.employee_id.department_id', string='القسم', store=True)

    request_type = fields.Selection([
        ('role', 'مسمّى وظيفي'),
        ('group', 'مجموعة أودو (صلاحية دقيقة)'),
        ('menu_show', 'إظهار قائمة مخفية'),
        ('emergency', 'صلاحية طوارئ (Break-glass)'),
    ], string='نوع الصلاحية', default='role', required=True, tracking=True)

    role_ids = fields.Many2many('care.job.role', 'care_access_req_role_rel', 'req_id', 'role_id',
                                string='المسمّيات المطلوبة')
    group_ids = fields.Many2many('res.groups', 'care_access_req_group_rel', 'req_id', 'group_id',
                                 string='المجموعات المطلوبة')
    menu_ids = fields.Many2many('ir.ui.menu', 'care_access_req_menu_rel', 'req_id', 'menu_id',
                                string='القوائم المطلوب إظهارها')

    duration_type = fields.Selection([('permanent', 'دائم'), ('temporary', 'مؤقّت')],
                                     string='المدّة', default='permanent', required=True, tracking=True)
    date_from = fields.Date(string='من تاريخ', default=fields.Date.context_today)
    date_to = fields.Date(string='إلى تاريخ', tracking=True,
                          help='للصلاحيات المؤقّتة: تُسحب تلقائيًّا بعد هذا التاريخ.')
    reason = fields.Text(string='السبب / المبرّر', required=True)
    company_id = fields.Many2one('res.company', string='الشركة', default=lambda s: s.env.company)

    approver_id = fields.Many2one('res.users', string='المعتمِد', readonly=True, tracking=True)
    reject_reason = fields.Char(string='سبب الرفض', readonly=True)
    summary = fields.Char(string='الصلاحية المطلوبة', compute='_compute_summary', store=True)

    # أثر التطبيق (للسحب الدقيق لاحقًا)
    applied = fields.Boolean(string='طُبّقت', readonly=True, copy=False)
    snapshot_id = fields.Many2one('care.access.snapshot', string='لقطة ما قبل التطبيق', readonly=True, copy=False)
    granted_role_ids = fields.Many2many('care.job.role', 'care_access_req_grole_rel', 'req_id', 'role_id',
                                        string='مسمّيات مُنحت فعلًا', readonly=True, copy=False)
    granted_group_ids = fields.Many2many('res.groups', 'care_access_req_ggroup_rel', 'req_id', 'group_id',
                                         string='مجموعات مُنحت فعلًا', readonly=True, copy=False)
    granted_menu_ids = fields.Many2many('ir.ui.menu', 'care_access_req_gmenu_rel', 'req_id', 'menu_id',
                                        string='قوائم أُظهرت فعلًا', readonly=True, copy=False)

    state = fields.Selection([
        ('draft', 'مسودة'), ('submitted', 'بانتظار الاعتماد'), ('approved', 'معتمد'),
        ('applied', 'مطبّق'), ('expired', 'منتهٍ'), ('rejected', 'مرفوض'), ('revoked', 'مسحوب')],
        string='الحالة', default='draft', tracking=True, index=True)

    _ESIGN_SUBMIT = ('مُقدّم الطلب', 'Requester')
    _ESIGN_APPROVE = ('مدير الصلاحيات', 'Access Manager')

    # ---------------- حسابات ----------------
    @api.depends('requester_id')
    def _compute_allowed_users(self):
        """المستخدمون الذين يجوز للمُقدّم طلب صلاحية لهم: هو نفسه + موظفوه
        (تسلسل التنظيم child_of + عمّال أقسام مشاريعه إن كان مدير مشروع). مدير النظام = الكل."""
        Emp = self.env['hr.employee'].sudo()
        Proj = self.env['project.project'].sudo()
        has_pms_dept = 'pms_department_id' in Proj._fields
        for r in self:
            req = r.requester_id or self.env.user
            if req.has_group('base.group_system') or req.has_group('care_access_hub.group_access_manager'):
                # المدير/مدير الصلاحيات: كل المستخدمين الداخليين
                r.allowed_user_ids = self.env['res.users'].sudo().search([('share', '=', False)])
                continue
            users = req  # هو نفسه
            emps = Emp.browse()
            if req.employee_id:
                emps |= Emp.search([('id', 'child_of', req.employee_id.id)])
            projs = Proj.search([('user_id', '=', req.id)])
            dept_ids = projs.mapped('pms_department_id').ids if has_pms_dept else []
            if dept_ids:
                emps |= Emp.search([('department_id', 'child_of', dept_ids)])
            users |= emps.mapped('user_id')
            r.allowed_user_ids = users

    @api.depends('request_type', 'role_ids', 'group_ids', 'menu_ids', 'duration_type', 'date_to')
    def _compute_summary(self):
        for r in self:
            if r.request_type == 'role':
                items = '، '.join(r.role_ids.mapped('name')) or '—'
                base = _('مسمّى: %s') % items
            elif r.request_type == 'group':
                items = '، '.join(r.group_ids.mapped('full_name')) or '—'
                base = _('مجموعة: %s') % items
            elif r.request_type == 'menu_show':
                items = '، '.join(r.menu_ids.mapped('complete_name')) or '—'
                base = _('إظهار قائمة: %s') % items
            else:
                items = '، '.join((r.group_ids | r.role_ids.mapped('odoo_group_ids')).mapped('full_name')) or '—'
                base = _('طوارئ: %s') % items
            if r.duration_type == 'temporary' and r.date_to:
                base += _(' (مؤقّت حتى %s)') % r.date_to
            r.summary = base

    # ---------------- قيود ----------------
    @api.constrains('duration_type', 'date_from', 'date_to', 'request_type')
    def _check_dates(self):
        for r in self:
            if r.duration_type == 'temporary':
                if not r.date_to:
                    raise ValidationError(_('الصلاحية المؤقّتة تتطلّب تاريخ انتهاء.'))
                if r.date_from and r.date_to < r.date_from:
                    raise ValidationError(_('تاريخ الانتهاء يجب أن يكون بعد تاريخ البداية.'))
            if r.request_type == 'emergency' and r.duration_type != 'temporary':
                raise ValidationError(_('صلاحية الطوارئ يجب أن تكون مؤقّتة (بتاريخ انتهاء).'))

    @api.constrains('request_type', 'role_ids', 'group_ids', 'menu_ids')
    def _check_payload(self):
        for r in self:
            if r.request_type == 'role' and not r.role_ids:
                raise ValidationError(_('اختر مسمّى وظيفيًّا واحدًا على الأقل.'))
            if r.request_type == 'group' and not r.group_ids:
                raise ValidationError(_('اختر مجموعة واحدة على الأقل.'))
            if r.request_type == 'menu_show' and not r.menu_ids:
                raise ValidationError(_('اختر قائمة واحدة على الأقل.'))
            if r.request_type == 'emergency' and not (r.group_ids or r.role_ids):
                raise ValidationError(_('حدّد المجموعات/المسمّيات المطلوبة للطوارئ.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('care.access.request') or 'AR/0001'
        return super().create(vals_list)

    # ---------------- أدوات ----------------
    def _is_mgr(self):
        u = self.env.user
        return u.has_group('care_access_hub.group_access_manager') or u.has_group('base.group_system')

    def _esign(self, role):
        self.ensure_one()
        Esign = self.env.get('care.esignature')
        if Esign is None:
            return
        try:
            Esign.sudo().esign_sign(self._name, self.id, role=role[0], role_en=role[1])
        except Exception:
            pass

    def _notify(self, users, title, body=''):
        """إشعار داخل أودو (رسالة) + دفع التطبيق إن توفّر مركز الإشعارات."""
        users = users.filtered(lambda u: u and u.partner_id)
        if not users:
            return
        try:
            self.message_post(body='%s — %s%s' % (title, self.name, ('\n' + body) if body else ''),
                              partner_ids=users.mapped('partner_id').ids,
                              subtype_xmlid='mail.mt_comment')
        except Exception:
            pass
        Push = self.env.get('care.cafm.notification')
        if Push is not None and hasattr(Push, 'push'):
            try:
                Push.sudo().push(users, title, body or self.summary or self.name)
            except Exception:
                pass

    def _approvers(self):
        """مدراء الصلاحيات (المعتمِدون) — مستبعِدًا مُقدّم الطلب (فصل الواجبات)."""
        grp = self.env.ref('care_access_hub.group_access_manager', raise_if_not_found=False)
        users = grp.users if grp else self.env['res.users']
        return users.filtered(lambda u: u.id != self.requester_id.id and not u.share)

    # ---------------- سير العمل ----------------
    def action_submit(self):
        for r in self:
            if r.state != 'draft':
                continue
            # فصل الواجبات (SoD): مُقدّم الطلب لا يعتمد طلبه بنفسه — يُنفَّذ عند الاعتماد.
            r.state = 'submitted'
            r._esign(r._ESIGN_SUBMIT)
            if r.requester_id and r.requester_id.partner_id:
                r.message_subscribe(partner_ids=r.requester_id.partner_id.ids)
            r._notify(r._approvers(), _('🗝️ طلب إضافة صلاحية جديد بانتظار اعتمادك'),
                      _('المستخدم: %s — %s') % (r.user_id.name, r.summary or ''))
        return True

    def action_approve(self):
        if not self._is_mgr():
            raise AccessError(_('اعتماد طلبات الصلاحية خاصّ بمدير الصلاحيات فقط.'))
        for r in self:
            if r.state not in ('submitted', 'draft'):
                continue
            # فصل الواجبات: لا يعتمد المستخدم طلبًا قدّمه بنفسه (إن فُعّلت الفكرة)
            comp = r.company_id or self.env.company
            if getattr(comp, 'ah_sod', True) and self.env.user.id == r.requester_id.id:
                raise UserError(_('فصل الواجبات: لا يمكنك اعتماد طلبٍ قدّمته بنفسك.'))
            r.state = 'approved'
            r.approver_id = self.env.user
            r._esign(r._ESIGN_APPROVE)
            r._apply()
            r._notify(r.requester_id | r.user_id, _('✅ تمّت الموافقة على طلب الصلاحية وتطبيقه'),
                      r.summary or '')
        return True

    def action_reject(self):
        if not self._is_mgr():
            raise AccessError(_('رفض طلبات الصلاحية خاصّ بمدير الصلاحيات فقط.'))
        for r in self:
            r.state = 'rejected'
            r.approver_id = self.env.user
            r._notify(r.requester_id | r.user_id, _('✖ تم رفض طلب الصلاحية'), r.reject_reason or '')
        return True

    def action_reset_draft(self):
        for r in self:
            if r.state in ('applied', 'revoked', 'expired'):
                raise UserError(_('لا يمكن إعادة طلبٍ طُبّق/سُحب إلى مسودة؛ استخدم «سحب الصلاحية».'))
            r.state = 'draft'
        return True

    def _apply(self):
        """يمنح الصلاحية فعليًّا — لقطة أمان أولًا، تتبّع الممنوح للسحب الدقيق، وتسجيل تدقيق."""
        self.ensure_one()
        Audit = self.env['care.access.audit'].sudo()
        snap = self.env['care.access.snapshot'].sudo().action_take_snapshot()
        self.snapshot_id = snap.id
        u = self.user_id.sudo()
        granted_roles = self.env['care.job.role']
        granted_groups = self.env['res.groups']
        granted_menus = self.env['ir.ui.menu']

        if self.request_type == 'role':
            new_roles = self.role_ids - u.care_role_ids
            if new_roles:
                u.write({'care_role_ids': [(4, r.id) for r in new_roles]})
                granted_roles = new_roles
            # امنح مجموعات المسمّيات (إضافة آمنة) وتتبّع الجديد منها فقط
            want = new_roles.mapped('odoo_group_ids')
            new_groups = want - u.groups_id
            if new_groups:
                u.write({'groups_id': [(4, g.id) for g in new_groups]})
                granted_groups = new_groups
        elif self.request_type in ('group', 'emergency'):
            want = self.group_ids | (self.role_ids.mapped('odoo_group_ids') if self.request_type == 'emergency' else self.env['res.groups'])
            new_groups = want - u.groups_id
            if new_groups:
                u.write({'groups_id': [(4, g.id) for g in new_groups]})
                granted_groups = new_groups
            if self.request_type == 'emergency':
                new_roles = self.role_ids - u.care_role_ids
                if new_roles:
                    u.write({'care_role_ids': [(4, r.id) for r in new_roles]})
                    granted_roles = new_roles
        elif self.request_type == 'menu_show':
            unhide = self.menu_ids & u.menu_hide_ids
            if unhide:
                u.write({'menu_hide_ids': [(3, m.id) for m in unhide]})
                granted_menus = unhide

        self.write({
            'applied': True, 'state': 'applied',
            'granted_role_ids': [(6, 0, granted_roles.ids)],
            'granted_group_ids': [(6, 0, granted_groups.ids)],
            'granted_menu_ids': [(6, 0, granted_menus.ids)],
        })
        Audit.log('access_grant', _('منح %(s)s للمستخدم %(u)s (طلب %(n)s)') % {
            's': self.summary or '', 'u': self.user_id.name, 'n': self.name})
        return True

    def action_revoke(self):
        """سحب الصلاحية الممنوحة يدويًّا (دقيق: يُزيل ما مُنح فعلًا فقط)."""
        if not self._is_mgr():
            raise AccessError(_('سحب الصلاحية خاصّ بمدير الصلاحيات فقط.'))
        for r in self:
            if r.state not in ('applied',):
                continue
            r._revoke(reason=_('سحب يدوي'), new_state='revoked')
            r._notify(r.requester_id | r.user_id, _('↩️ سُحبت الصلاحية الممنوحة'), r.summary or '')
        return True

    def _revoke(self, reason='', new_state='revoked'):
        self.ensure_one()
        u = self.user_id.sudo()
        if self.granted_role_ids:
            u.write({'care_role_ids': [(3, r.id) for r in self.granted_role_ids]})
        if self.granted_group_ids:
            u.write({'groups_id': [(3, g.id) for g in self.granted_group_ids]})
        if self.granted_menu_ids:
            u.write({'menu_hide_ids': [(4, m.id) for m in self.granted_menu_ids]})
        self.state = new_state
        self.env['care.access.audit'].sudo().log(
            'access_revoke', _('سحب %(s)s من %(u)s (%(r)s — طلب %(n)s)') % {
                's': self.summary or '', 'u': self.user_id.name, 'r': reason, 'n': self.name})
        return True

    @api.model
    def cron_revoke_expired(self):
        """كرون: يسحب تلقائيًّا الصلاحيات المؤقّتة المنتهية ويُشعر."""
        today = fields.Date.today()
        expired = self.sudo().search([
            ('state', '=', 'applied'), ('duration_type', '=', 'temporary'),
            ('date_to', '!=', False), ('date_to', '<', today)])
        for r in expired:
            r._revoke(reason=_('انتهاء المدّة'), new_state='expired')
            r._notify(r.requester_id | r.user_id, _('⏳ انتهت صلاحية مؤقّتة وسُحبت تلقائيًّا'), r.summary or '')
        return True

    def action_open(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('طلب صلاحية'),
                'res_model': self._name, 'res_id': self.id, 'view_mode': 'form', 'views': [(False, 'form')]}
