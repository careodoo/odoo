# -*- coding: utf-8 -*-
# ============================================================================
# The layer applying the "employee view profile" to actual operation:
#  - hr.employee._care_view_access(): the effective config for the current user (or None for admin).
#  - hr.employee.care_civilid_display: a masked civil ID for the cards per the field rule.
#  - ir.ui.menu._visible_menu_ids(): hides the menus not permitted to the viewer.
# The admin (HR manager / system administrator) is not restricted at all.
# ============================================================================
from odoo import api, fields, models


class CareAccessProfileUser(models.Model):
    _inherit = 'care.access.profile'

    @api.model
    def _for_user(self, uid=None):
        """ملفّات «عرض الموظفين» النشطة المسنَدة للمستخدم (عدا الأدمن)."""
        uid = uid or self.env.uid
        user = self.env['res.users'].browse(uid)
        # The admin is not restricted
        if user.has_group('base.group_system') or user.has_group('hr.group_hr_manager'):
            return self.browse()
        return self.sudo().search([
            ('is_employee_view', '=', True),
            ('active', '=', True),
            ('user_ids', 'in', uid),
        ])


class HrEmployeeAccess(models.Model):
    _inherit = 'hr.employee'

    # A civil ID prepared for the cards (kanban) — respects the viewer's field rule
    care_civilid_display = fields.Char(
        string='Civil ID (display)', compute='_compute_care_civilid_display',
        compute_sudo=False)

    @api.depends('civil_code', 'identification_id')
    def _compute_care_civilid_display(self):
        acc = self.env['hr.employee']._care_view_access()
        fmodes = (acc or {}).get('field_modes', {})
        # We take the strictest mode of the two fields shown on the card
        mode = 'show'
        for fn in ('civil_code', 'identification_id'):
            m = fmodes.get(fn)
            if m == 'hide':
                mode = 'hide'
                break
            if m == 'mask':
                mode = 'mask'
        for rec in self:
            sr = rec.sudo()
            raw = sr.civil_code or sr.identification_id or ''
            if not acc:
                rec.care_civilid_display = raw or '—'
            elif mode == 'hide':
                rec.care_civilid_display = '—'
            elif mode == 'mask':
                rec.care_civilid_display = '••••' if raw else '—'
            else:
                rec.care_civilid_display = raw or '—'

    @api.model
    def _care_view_access(self):
        """الإعداد الفعّال لـ«عرض الموظفين» للمستخدم الحالي، أو None إن كان غير مقيَّد.

        عند تعدّد الملفّات (نادر): الأشدّ تقييداً — اتحاد الأقسام/الحقول المخفيّة،
        وأدنى مستوى عرض. يُفترض ملف واحد لكل مستخدم."""
        profiles = self.env['care.access.profile']._for_user()
        if not profiles:
            return None
        lvl_rank = {'basic': 1, 'ext': 2, 'full': 3}
        rank_lvl = {1: 'basic', 2: 'ext', 3: 'full'}

        hidden_sections = set()
        field_modes = {}
        view_rank = 3
        hide_dashboard = False
        readonly = True
        watermark = False
        can_export = False
        can_print = False
        audit = False
        for p in profiles:
            view_rank = min(view_rank, lvl_rank.get(p.emp_view_level, 1))
            # Hidden sections = those with visible=False
            for sline in p.emp_section_ids:
                if not sline.visible:
                    hidden_sections.add(sline.section_key)
            # Field rules — the strictest wins (hide > mask > show)
            order = {'show': 0, 'mask': 1, 'hide': 2}
            for fline in p.emp_field_ids:
                fn = fline.field_name or (fline.field_id.name if fline.field_id else None)
                if not fn:
                    continue
                cur = field_modes.get(fn)
                if cur is None or order[fline.mode] > order[cur]:
                    field_modes[fn] = fline.mode
            hide_dashboard = hide_dashboard or p.emp_hide_dashboard
            readonly = readonly and (p.emp_level == 'read')
            watermark = watermark or p.emp_watermark
            can_export = can_export or p.emp_can_export
            can_print = can_print or p.emp_can_print
            audit = audit or p.emp_audit
        return {
            'profile_ids': profiles.ids,
            'view_level': rank_lvl[view_rank],
            'hidden_sections': hidden_sections,
            'field_modes': field_modes,
            'hide_dashboard': hide_dashboard,
            'readonly': readonly,
            'watermark': watermark,
            'can_export': can_export,
            'can_print': can_print,
            'audit': audit,
        }


class IrUiMenuAccess(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def _visible_menu_ids(self, debug=False):
        """يحجب قوائم «عرض الموظفين» غير المسموح بها. بلا ذاكرة خاصّة —
        يعتمد على ذاكرة الأساس عبر super ويحسب التعديل per-user في كل نداء
        (نفس نمط care_menu_perm المُثبَت)، وإلا تعارض الذاكرة مع تصفية search."""
        ids = set(super()._visible_menu_ids(debug=debug))
        # Admin and the root user: no restriction
        if self.env.su or self.env.user.has_group('base.group_system') \
                or self.env.user.has_group('hr.group_hr_manager'):
            return ids
        profiles = self.env['care.access.profile']._for_user()
        if not profiles:
            return ids
        Menu = self.env['ir.ui.menu'].sudo().with_context(active_test=False)

        def ancestors(menu_ids):
            out = set()
            menus = Menu.browse(list(menu_ids))
            for m in menus:
                p = m.parent_id
                while p:
                    out.add(p.id)
                    p = p.parent_id
            return out

        def descendants(menu_ids):
            """القائمة + كل نسلها عبر parent_path مباشرة من SQL — موثوق وغير
            مُرشَّح (نتجنّب ir.ui.menu.search التي تُرشّح بالرؤية وتُسبّب تكراراً،
            وتفشل مع parent_id المعاد ربطه)."""
            menu_ids = [m for m in menu_ids if m]
            if not menu_ids:
                return set()
            clauses, params = [], []
            for mid in menu_ids:
                clauses.append('parent_path LIKE %s OR parent_path LIKE %s')
                params.extend(['%s/%%' % mid, '%%/%s/%%' % mid])
            self.env.cr.execute(
                'SELECT id FROM ir_ui_menu WHERE ' + ' OR '.join(clauses), params)
            return {r[0] for r in self.env.cr.fetchall()}

        # The access profile's scope of effect = the employees app tree only (hr.menu_hr_root).
        # The rest of the system's menus/apps are left as-is (governed by the groups and the
        # Menu View Permissions = care_menu_perm module). This way the employees profile does not hide
        # the system's other apps (purchases/collections/…), but controls the employees menus alone.
        hr_root = self.env.ref('hr.menu_hr_root', raise_if_not_found=False)
        hr_tree = descendants({hr_root.id}) if hr_root else set()

        # 1) "Show selected only": within the employees tree, shows the selected menus
        #    + only their parents' path and hides the rest of the employees menus. Menus outside the
        #    employees tree stay as the base returned them (this mode does not touch them).
        only_allowed = set()
        has_only = False
        for p in profiles:
            if p.emp_menu_mode == 'only' and p.emp_menu_ids:
                has_only = True
                sel = set(p.emp_menu_ids.ids)
                only_allowed |= sel | ancestors(sel)
        if has_only and hr_tree:
            outside_hr = ids - hr_tree          # Everything outside employees stays
            inside_allowed = only_allowed & hr_tree   # What is allowed within employees
            ids = outside_hr | inside_allowed
        # 2) "Hide selected" menus (+ their children) — restricted to the employees tree
        for p in profiles:
            if p.emp_menu_mode == 'hide' and p.emp_menu_ids:
                ids -= (descendants(set(p.emp_menu_ids.ids)) & hr_tree)
        # 3) Hide the statistics dashboard
        if any(p.emp_hide_dashboard for p in profiles):
            dash = self.env.ref('care_hr.menu_hr_dashboard', raise_if_not_found=False)
            if dash:
                ids.discard(dash.id)
        # 4) احترام إخفاء care_access_hub الموحّد (role.menu_hide_ids/user.menu_hide_ids):
        #    وضع «only» أعلاه يُعيد إظهار قوائم الموظفين المسموحة — لكن يجب ألّا يتجاوز
        #    إخفاء نظام الصلاحيات الموحّد (وإلا يظهر تطبيق «الموظفين» لأدوار أُخفي عنها).
        try:
            u = self.env.user.sudo()
            ah_hide = set()
            if 'menu_hide_ids' in u._fields:
                ah_hide |= set(u.menu_hide_ids.ids)
            if 'care_role_ids' in u._fields and u.care_role_ids:
                rsets = [set(r.menu_hide_ids.ids) for r in u.care_role_ids]
                if rsets:
                    ah_hide |= set.intersection(*rsets)
            if ah_hide:
                ids -= ah_hide
        except Exception:
            pass
        return ids
