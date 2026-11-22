# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = 'res.users'

    # مسمّيات متعددة للمستخدم الواحد — الصلاحية الفعلية = اتحاد (الأعلى)
    care_role_ids = fields.Many2many(
        'care.job.role', 'care_user_role_rel', 'user_id', 'role_id',
        string='المسمّيات الوظيفية')
    care_role_label = fields.Char(string='المسمّيات', compute='_compute_role_label')
    # «إشعاراتي»: الأنواع التي تصل المستخدم فعلًا (حسب صلاحياته) + تحكّمه فيها
    notify_pref_ids = fields.One2many('care.user.notify.pref', 'user_id', string='إشعاراتي')
    # «تفويضاتي»: التفويضات التي يمنحها هذا المستخدم لآخرين
    delegation_ids = fields.One2many('care.user.delegation', 'delegator_id', string='تفويضاتي')
    # «طلبات الصلاحية»: الطلبات التي قدّمها هذا المستخدم (خدمة ذاتية من الملف الشخصي)
    my_access_request_ids = fields.One2many('care.access.request', 'requester_id',
                                            string='طلباتي للصلاحيات')
    # قوائم مخفية لكل مستخدم (المكان الموحّد — بدل شاشة وصول القوائم المنفصلة)
    menu_hide_ids = fields.Many2many('ir.ui.menu', 'care_user_menu_hide_rel', 'user_id', 'menu_id',
                                     string='القوائم المخفية عن هذا المستخدم')

    def write(self, vals):
        res = super().write(vals)
        # تحديث «إشعاراتي» تلقائيًّا عند تغيّر مسمّيات المستخدم (بلا حاجة لزرّ)
        if 'care_role_ids' in vals and not self.env.context.get('ah_syncing_notify'):
            try:
                self.with_context(ah_syncing_notify=True).filtered(
                    lambda u: not u.share)._ah_do_sync_notify_prefs()
            except Exception:
                pass
        return res

    def _ah_relevant_channels(self):
        """أنواع الإشعارات التي يصلها هذا المستخدم فعلًا (هو معتمِد محتمل حسب صلاحياته/مسمّياته).
        مُحسَّن: يجلب القنوات وأنواع الاعتماد دفعة واحدة بدل بحثٍ لكل نوع."""
        self.ensure_one()
        Center = self.env.get('care.approval.center')
        Ch = self.env['care.access.notify.channel'].sudo()
        if Center is None:
            return Ch.browse()
        my_groups = set(self.groups_id.ids)
        my_roles = set(self.care_role_ids.ids)
        broad = {'base.group_user', 'base.group_portal', 'base.group_public'}
        # جلب دفعة واحدة (أداء)
        ch_by_key = {c.key: c for c in Ch.search([])}
        AT = self.env.get('care.approval.type')
        type_by_model = {}
        if AT is not None:
            type_by_model = {t.model_name: t for t in AT.sudo().search([]) if t.model_name}
        # ذاكرة مؤقّتة لمراجع المجموعات (xmlid → id)
        grp_cache = {}

        def _gid(xmlid):
            if xmlid not in grp_cache:
                g = self.env.ref(xmlid, raise_if_not_found=False)
                grp_cache[xmlid] = g.id if g else False
            return grp_cache[xmlid]

        relevant = Ch.browse()
        for e in Center.sudo()._entries():
            ch = ch_by_key.get(e.get('key'))
            ch_off = ch and not (ch.ch_app or ch.ch_odoo or ch.ch_email)
            if not ch or ch_off:
                if not (ch and ch.mandatory):
                    continue
            # مسمّيات/مستخدمو مراحل النوع (منظومة الصلاحيات)
            has_config = False
            match = False
            t = type_by_model.get(e.get('model'))
            if t:
                sroles = set(t.stage_ids.mapped('role_ids').ids)
                susers = set(t.stage_ids.mapped('extra_user_ids').ids)
                if sroles or susers:
                    has_config = True
                    match = bool(my_roles & sroles) or (self.id in susers)
            if not has_config:
                for g in e.get('groups') or []:
                    if g in broad:
                        continue
                    gid = _gid(g)
                    if gid and gid in my_groups:
                        match = True
                        break
            if match or (ch and ch.mandatory):
                relevant |= ch
        return relevant

    def _ah_do_sync_notify_prefs(self):
        """يملأ «إشعاراتي» بالأنواع التي تصل المستخدم (حسب صلاحياته)، مع إبقاء تفضيلاته."""
        Pref = self.env['care.user.notify.pref'].sudo()
        for u in self:
            relevant = u._ah_relevant_channels()
            existing = {p.channel_id.id: p for p in u.notify_pref_ids}
            for ch in relevant:
                if ch.id not in existing:
                    Pref.create({'user_id': u.id, 'channel_id': ch.id,
                                 'use_app': True, 'use_odoo': True, 'use_email': True})
            for p in u.notify_pref_ids:
                if p.channel_id.id not in relevant.ids:
                    p.unlink()
        return True

    def action_sync_notify_prefs(self):
        """زرّ «تحميل/تحديث إشعاراتي»."""
        self._ah_do_sync_notify_prefs()
        return {'type': 'ir.actions.client', 'tag': 'reload'}
    # عدّاد مجموعات أودو الحالية — لإظهار فوضى الإسناد العشوائي (110 متوسّط)
    care_group_count = fields.Integer(string='عدد المجموعات الحالية', compute='_compute_group_count')

    @api.depends('care_role_ids')
    def _compute_role_label(self):
        for u in self:
            u.care_role_label = ' + '.join(u.care_role_ids.mapped('name')) or ''

    @api.depends('groups_id')
    def _compute_group_count(self):
        for u in self:
            u.care_group_count = len(u.groups_id)

    # محلّل الفرق (diff): المبرّر بالمسمّيات مقابل الزائد العشوائي — dry-run آمن
    care_role_group_ids = fields.Many2many(
        'res.groups', string='مجموعات المسمّيات', compute='_compute_diff')
    care_excess_count = fields.Integer(string='مجموعات زائدة (غير مبرّرة)', compute='_compute_diff')
    care_missing_count = fields.Integer(string='مجموعات ناقصة (يحتاجها المسمّى)', compute='_compute_diff')

    @api.depends('care_role_ids', 'care_role_ids.odoo_group_ids', 'groups_id')
    def _compute_diff(self):
        ess = self.env.ref('base.group_user', raise_if_not_found=False)
        for u in self:
            rg = u.care_role_ids.mapped('odoo_group_ids')
            u.care_role_group_ids = rg
            excess = u.groups_id - rg
            if ess:
                excess = excess - ess
            u.care_excess_count = len(excess)
            u.care_missing_count = len(rg - u.groups_id)

    def action_access_diff(self):
        """معاينة الفرق: المبرّر / الزائد / الناقص — بلا أي تعديل."""
        self.ensure_one()
        msg = _(
            'المسمّيات: %(r)s\nمجموعات حالية: %(cur)s\nمبرّرة بالمسمّيات: %(j)s\n'
            '⚠️ زائدة (مرشّحة للتجريد): %(x)s\nناقصة (يحتاجها المسمّى): %(m)s'
        ) % {
            'r': self.care_role_label or '—', 'cur': len(self.groups_id),
            'j': len(self.care_role_group_ids), 'x': self.care_excess_count,
            'm': self.care_missing_count,
        }
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('تحليل صلاحيات %s') % self.name,
                           'message': msg, 'sticky': True, 'type': 'warning'}}

    def action_strip_excess(self):
        """يُجرّد المجموعات الزائدة غير المبرّرة بالمسمّى — لقطة احتياطية تلقائية أولًا،
        حماية مجموعات النظام/الأدمن من الإزالة، وتسجيل تدقيق. خاصّ بمدير المنظومة."""
        if not self.env.user.has_group('care_access_hub.group_access_manager') \
                and not self.env.user.has_group('base.group_system'):
            raise UserError(_('التجريد خاصّ بمدير منظومة الصلاحيات.'))
        protect = (self.env.ref('base.group_system') | self.env.ref('base.group_erp_manager')
                   | self.env.ref('base.group_portal') | self.env.ref('base.group_public')
                   | self.env.ref('base.group_user'))
        # لقطة أمان قبل أي تعديل (تُتيح العكس لاحقًا)
        snap = self.env['care.access.snapshot'].sudo().action_take_snapshot()
        done = []
        for u in self:
            if not u.care_role_ids:
                continue
            rg = u.care_role_ids.mapped('odoo_group_ids')
            strip = u.groups_id - rg - protect
            if not strip:
                continue
            before = len(u.groups_id)
            u.sudo().write({'groups_id': [(3, g.id) for g in strip]})
            u.invalidate_recordset()
            self.env['care.access.audit'].sudo().log(
                'strip', _('تجريد %(n)s مجموعة من %(u)s (%(b)s→%(a)s)') % {
                    'n': len(strip), 'u': u.name, 'b': before, 'a': len(u.groups_id)})
            done.append('%s: %s→%s' % (u.name, before, len(u.groups_id)))
        if not done:
            return {'type': 'ir.actions.client', 'tag': 'display_notification',
                    'params': {'title': _('التجريد'),
                               'message': _('لا فائض قابل للتجريد (بلا مسمّى أو بلا فائض).'),
                               'sticky': False, 'type': 'warning'}}
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('تمّ التجريد — لقطة العكس #%s') % snap.id,
                           'message': '\n'.join(done), 'sticky': True, 'type': 'success'}}

    # ---------- إنفاذ نطاق الشركات (متعدد الشركات الأصلي) ----------
    def _ah_role_companies(self):
        """الشركات المسموح بها للمستخدم مُشتقّة من مسمّياته:
        None=بلا مسمّى (لا تغيير)، كل الشركات=إن كان أي مسمّى «كل الشركات» (company_ids فارغ)."""
        self.ensure_one()
        roles = self.care_role_ids
        if not roles:
            return None
        if any(not r.company_ids for r in roles):
            return self.env['res.company'].sudo().search([])
        comps = self.env['res.company']
        for r in roles:
            comps |= r.company_ids
        return comps

    def action_preview_company_scope(self):
        """معاينة نطاق الشركات المُشتقّ من المسمّيات — dry-run بلا تعديل."""
        self.ensure_one()
        comps = self._ah_role_companies()
        if comps is None:
            msg = _('لا مسمّى مُسنَد — لا تغيير على الشركات.')
        else:
            msg = _('الشركات المسموح بها من المسمّيات: %s') % ('، '.join(comps.mapped('name')) or '—')
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('نطاق الشركات: %s') % self.name, 'message': msg,
                           'sticky': True, 'type': 'info'}}

    def action_apply_company_scope(self):
        """يضبط «الشركات المسموح بها» للمستخدم من نطاق شركات مسمّياته (آلية أودو الأصلية).
        آمن: يُبقي الشركة الحالية ضمن المسموح (منعًا للقفل)؛ خاصّ بمدير المنظومة؛ يُسجَّل تدقيقًا."""
        if not self.env.user.has_group('care_access_hub.group_access_manager') \
                and not self.env.user.has_group('base.group_system'):
            raise UserError(_('ضبط نطاق الشركات خاصّ بمدير منظومة الصلاحيات.'))
        done = []
        for u in self:
            comps = u._ah_role_companies()
            if comps is None or not comps:
                continue
            if u.company_id and u.company_id.id not in comps.ids:
                comps |= u.company_id  # لا تُقصِ شركته الحالية
            before = len(u.company_ids)
            if set(u.company_ids.ids) == set(comps.ids):
                continue
            u.sudo().write({'company_ids': [(6, 0, comps.ids)]})
            self.env['care.access.audit'].sudo().log(
                'company_scope', _('نطاق شركات %(u)s = %(c)s') % {
                    'u': u.name, 'c': '، '.join(comps.mapped('name'))})
            done.append('%s: %s→%s شركة' % (u.name, before, len(comps)))
        msg = '\n'.join(done) if done else _('لا تغيير (بلا مسمّى مُقيَّد بشركات).')
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('نطاق الشركات'), 'message': msg,
                           'sticky': bool(done), 'type': 'success' if done else 'warning'}}

    def action_apply_roles(self):
        """تطبيق آمن (إضافة فقط): يمنح المستخدم مجموعات مسمّياته دون حذف شيء.
        التجريد الكامل للعشوائية مرحلة ترحيل لاحقة مُبوّبة ومُختبَرة."""
        for u in self:
            grps = u.care_role_ids.mapped('odoo_group_ids')
            if grps:
                u.sudo().write({'groups_id': [(4, g.id) for g in grps]})
        return True

    # ---------- بيانات تقرير صلاحيات المستخدم (احترافي + خانة اعتماد) ----------
    def _access_report(self):
        """يُجمّع صلاحيات المستخدم الفعلية للتقرير (مسمّيات/شركات/مجموعات/قوائم/حقول/اعتمادات/تفويضات/إشعارات)."""
        self.ensure_one()
        u = self.sudo()
        # المسمّيات
        roles = [{'name': r.name, 'tier': dict(r._fields['tier'].selection).get(r.tier, r.tier),
                  'scope': 'كل الشركة' if r.data_scope == 'all' else 'مشاريعه فقط',
                  'approve': r.can_approve} for r in u.care_role_ids]
        # الشركات
        companies = u.company_ids.mapped('name')
        # المجموعات مجمّعة بالتصنيف
        by_cat = {}
        for g in u.groups_id:
            cat = g.category_id.name or 'أخرى'
            by_cat.setdefault(cat, []).append(g.name)
        groups_by_cat = [{'cat': c, 'groups': sorted(v)} for c, v in sorted(by_cat.items())]
        # القوائم المخفية
        menu_hides = sorted(set(u.menu_hide_ids.mapped('complete_name')))
        # الحقول المخفية (من المسمّيات)
        Mask = self.env['care.role.field.mask'].sudo()
        masks = Mask.search([('role_id', 'in', u.care_role_ids.ids), ('hidden', '=', True)])
        field_masks = sorted({'%s · %s' % (m.model_name, m.field_label or m.field_name) for m in masks})
        # صلاحيات الاعتماد (المستخدم معتمِد في مراحل هذه الأنواع)
        approvals = []
        AT = self.env.get('care.approval.type')
        if AT is not None:
            my_roles = set(u.care_role_ids.ids)
            for t in AT.sudo().search([]):
                for s in t.stage_ids:
                    if (set(s.role_ids.ids) & my_roles) or (u.id in s.extra_user_ids.ids):
                        approvals.append({'type': t.name, 'stage': s.name,
                                          'mode': dict(s._fields['mode'].selection).get(s.mode, s.mode)})
        # التفويضات
        deleg_given = [{'to': d.delegate_id.name, 'scope': 'كل الأنواع' if d.scope == 'all' else 'مخصّص',
                        'from': d.date_from and d.date_from.strftime('%Y/%m/%d') or '—',
                        'to_date': d.date_to and d.date_to.strftime('%Y/%m/%d') or '—',
                        'state': dict(d._fields['state'].selection).get(d.state, d.state)}
                       for d in u.delegation_ids]
        Deleg = self.env['care.user.delegation'].sudo()
        deleg_recv = [{'from_user': d.delegator_id.name, 'scope': 'كل الأنواع' if d.scope == 'all' else 'مخصّص',
                       'to_date': d.date_to and d.date_to.strftime('%Y/%m/%d') or '—',
                       'state': dict(d._fields['state'].selection).get(d.state, d.state)}
                      for d in Deleg.search([('delegate_id', '=', u.id)])]
        # إشعارات الاعتماد
        notify = [{'name': p.channel_name, 'channels': p.channel_id.channels_label,
                   'mandatory': p.mandatory} for p in u.notify_pref_ids]
        return {
            'roles': roles, 'companies': companies, 'group_count': len(u.groups_id),
            'groups_by_cat': groups_by_cat, 'menu_hides': menu_hides, 'field_masks': field_masks,
            'approvals': approvals, 'deleg_given': deleg_given, 'deleg_recv': deleg_recv,
            'notify': notify, 'role_label': u.care_role_label or '—',
        }

    def action_print_access(self):
        self.ensure_one()
        return self.env.ref('care_access_hub.action_report_user_access').report_action(self)

    def action_preview_effective(self):
        """معاينة الصلاحية الفعلية (اتحاد المسمّيات) — dry-run لا يعدّل شيئًا."""
        self.ensure_one()
        roles = self.care_role_ids
        scope = 'كل الشركة' if any(r.data_scope == 'all' for r in roles) else 'مشاريعه فقط'
        groups = roles.mapped('odoo_group_ids')
        msg = _('المسمّيات: %(roles)s\nنطاق البيانات: %(scope)s\nمجموعات أودو المقترحة: %(n)s') % {
            'roles': self.care_role_label or '—', 'scope': scope, 'n': len(groups)}
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('المعاينة الفعلية'), 'message': msg, 'sticky': True, 'type': 'info'},
        }
