# -*- coding: utf-8 -*-
# صلاحيات القوائم (Menu View Permissions — جوهر الموكاب): إخفاء قوائم لكل مسمّى.
# الإنفاذ على مستوى العرض بلا مساس بـgroups_id المخزّنة. يوحّد وظيفة care_menu_perm داخل النظام الجديد.
from odoo import api, models


class IrUiMenuAccessHub(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def _visible_menu_ids(self, debug=False):
        ids = super()._visible_menu_ids(debug=debug)
        try:
            return self._ah_filter_menus(set(ids))
        except Exception:
            return ids  # لا نكسر القوائم أبدًا

    def _ah_filter_menus(self, ids):
        env = self.env
        # الأدمن/سودو يرى كل شيء
        if env.su or env.user.has_group('base.group_system'):
            return ids
        if 'care_role_ids' not in env.user._fields:
            return ids
        roles = env.user.sudo().care_role_ids
        if not roles:
            return ids
        # تُخفى القائمة فقط إن أخفتها «كل» مسمّيات المستخدم (الأكثر تساهلًا يفوز) = تقاطع
        sets = [set(r.menu_hide_ids.ids) for r in roles]
        hide = set.intersection(*sets) if sets else set()
        return ids - hide if hide else ids
