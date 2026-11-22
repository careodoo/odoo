# -*- coding: utf-8 -*-
# تطبيق إخفاء الحقول (الفكرة ah_field_mask): يُخفي الحقول المُعلَّمة «مخفي 🔒»
# عن مستخدمٍ حسب مسمّياته، على مستوى العرض (form/tree).
# حماية الإنتاج:
#  - يتجاوز الأدمن/سودو تمامًا.
#  - يُخفي حقلًا فقط إن كان مخفيًّا في «كل» مسمّيات المستخدم (الأكثر تساهلًا يفوز) — يميل للإظهار.
#  - مُغلّف بـtry/except؛ أي فشل = العرض الأصلي بلا مساس.
#  - مُعطَّل إن أُطفئ ah_field_mask على الشركة.
from collections import Counter
from lxml import etree
from odoo import api, models


class BaseFieldMask(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type not in ('form', 'tree', 'kanban'):
            return res
        try:
            self._ah_apply_field_masks(res, view_type)
        except Exception:
            pass  # لا نكسر العرض أبدًا
        return res

    def _ah_hidden_fields(self):
        """أسماء الحقول التي يجب إخفاؤها عن المستخدم الحالي لهذا المودل (أو None)."""
        env = self.env
        # تجاوز الأدمن/سودو
        if env.su or env.user.has_group('base.group_system'):
            return None
        if 'care_role_ids' not in env.user._fields:
            return None
        roles = env.user.sudo().care_role_ids
        if not roles:
            return None
        company = env.company
        if 'ah_field_mask' in company._fields and not company.ah_field_mask:
            return None
        Mask = env['care.role.field.mask'].sudo()
        masks = Mask.search([('role_id', 'in', roles.ids),
                             ('model_name', '=', self._name), ('hidden', '=', True)])
        if not masks:
            return None
        # مخفي فقط إن كان مخفيًّا في كل مسمّيات المستخدم (الأكثر تساهلًا يفوز)
        cnt = Counter(masks.mapped('field_name'))
        nroles = len(roles)
        hidden = {f for f, c in cnt.items() if c >= nroles}
        return hidden or None

    def _ah_apply_field_masks(self, res, view_type):
        hidden = self._ah_hidden_fields()
        if not hidden:
            return
        arch = etree.fromstring(res['arch'])
        changed = False
        for fname in hidden:
            for node in arch.xpath("//field[@name='%s']" % fname):
                node.set('invisible', '1')
                node.set('readonly', '1')
                node.set('force_save', '0')
                changed = True
        if changed:
            res['arch'] = etree.tostring(arch, encoding='unicode')
