# -*- coding: utf-8 -*-
# صلاحيات القوائم الموحّدة داخل care_access_hub — المكان الوحيد لتحديد رؤية القوائم:
#  (أ) إخفاء لكل مسمّى وظيفي (menu_hide_ids على care.job.role).
#  (ب) وصول لكل مستخدم/قائمة (care.menu.access): قائمة بيضاء (حصر) + سوداء (إخفاء) — يحاكي care_menu_perm تمامًا.
# الإنفاذ على مستوى العرض بلا مساس بـgroups_id. يُلغي الحاجة لموديول care_menu_perm (مكان واحد بلا تضارب).
from odoo import api, fields, models


class CareMenuAccess(models.Model):
    """وصول قائمة لمستخدمين محدّدين (مُرحَّل/موحّد من care_menu_perm)."""
    _name = 'care.menu.access'
    _description = 'وصول قائمة (حصر/إخفاء)'
    _rec_name = 'menu_id'

    menu_id = fields.Many2one('ir.ui.menu', string='القائمة', required=True, ondelete='cascade', index=True)
    menu_path = fields.Char(related='menu_id.complete_name', string='مسار القائمة', store=True)
    allow_user_ids = fields.Many2many('res.users', 'care_menu_access_allow_rel', 'access_id', 'user_id',
                                      string='حصر على (قائمة بيضاء)',
                                      help='إن حُدِّد مستخدمون هنا، لا يرى القائمة إلا هم.')
    hide_user_ids = fields.Many2many('res.users', 'care_menu_access_hide_rel', 'access_id', 'user_id',
                                     string='إخفاء عن (قائمة سوداء)',
                                     help='المستخدمون هنا لا يرون هذه القائمة.')

    _sql_constraints = [('menu_uniq', 'unique(menu_id)', 'للقائمة سطر وصول واحد.')]

    @api.model
    def migrate_from_menu_perm(self):
        """ترحيل قيود care_menu_perm (قائمة بيضاء/سوداء) إلى هنا — مكان واحد."""
        MP = self.env.get('care.menu.perm')
        if MP is None:
            return 0
        n = 0
        for p in MP.sudo().search([('active', '=', True)]):
            wl = (p.see_user_ids | p.read_user_ids | p.write_user_ids | p.delete_user_ids)
            bl = p.hide_user_ids
            if not wl and not bl:
                continue
            acc = self.sudo().search([('menu_id', '=', p.menu_id.id)], limit=1)
            vals = {}
            if wl:
                vals['allow_user_ids'] = [(6, 0, wl.ids)]
            if bl:
                vals['hide_user_ids'] = [(6, 0, bl.ids)]
            if acc:
                acc.write(vals)
            else:
                vals['menu_id'] = p.menu_id.id
                self.sudo().create(vals)
                n += 1
        return n


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
        uid = env.uid
        ids = set(ids)
        # (أ) وصول لكل قائمة/مستخدم (مُرحَّل من care_menu_perm) — يسري على كل المستخدمين
        Access = env.get('care.menu.access')
        if Access is not None:
            acc = Access.sudo()
            for a in acc.search([('allow_user_ids', '!=', False)]):
                if uid not in a.allow_user_ids.ids:
                    ids.discard(a.menu_id.id)  # حصر: لست ضمن المسموح لهم
            for a in acc.search([('hide_user_ids', 'in', uid)]):
                ids.discard(a.menu_id.id)      # إخفاء عنّي
        # (ب) إخفاء لكل مسمّى (للمستخدمين الداخليين ذوي المسمّيات)
        if 'care_role_ids' in env.user._fields:
            roles = env.user.sudo().care_role_ids
            if roles:
                sets = [set(r.menu_hide_ids.ids) for r in roles]
                hide = set.intersection(*sets) if sets else set()
                ids -= hide
        return ids
