# -*- coding: utf-8 -*-
# إخفاء القوائم الموحّد داخل care_access_hub — المكان الوحيد لتحديد رؤية القوائم:
#  (أ) إخفاء لكل مستخدم: menu_hide_ids على res.users (المكان الموحّد — استُبدلت به شاشة «وصول القوائم»
#      وموديل care.menu.access وموديول care_menu_perm القديم؛ رُحِّلت بياناتها كلها إلى هنا).
#  (ب) إخفاء لكل مسمّى وظيفي: menu_hide_ids على care.job.role (يُطبَّق عند تقاطع كل مسمّيات المستخدم).
# الإنفاذ على مستوى العرض بلا مساس بـgroups_id — لا تضارب مع المجموعات أو بطاقة المستخدم.
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
        if env.su or env.user.has_group('base.group_system'):
            return ids  # الأدمن يرى كل شيء
        ids = set(ids)
        u = env.user.sudo()
        # (أ) قوائم مخفية لكل مستخدم (المكان الموحّد في صلاحيات المستخدم)
        if 'menu_hide_ids' in u._fields:
            ids -= set(u.menu_hide_ids.ids)
        # (ب) إخفاء لكل مسمّى (الأكثر تساهلًا يفوز = تقاطع مسمّياته)
        if 'care_role_ids' in u._fields:
            roles = u.care_role_ids
            if roles:
                sets = [set(r.menu_hide_ids.ids) for r in roles]
                hide = set.intersection(*sets) if sets else set()
                ids -= hide
        return ids
