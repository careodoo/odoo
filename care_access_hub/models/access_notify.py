# -*- coding: utf-8 -*-
# منظومة إشعارات الاعتماد (تبويب «الإشعارات» في الموكاب):
#  - إعداد الإدارة: قناة لكل نوع اعتماد (📧 بريد / 🔔 فوري / 🔕 بلا) + علامة «إلزامي» تُقفل على المستخدم.
#  - تفضيل المستخدم: تعطيل أنواع غير إلزامية من لوحته (البورتال والداخلي).
#  - مربوطة بمركز الموافقات: كرون الإشعارات يستشير القناة الفعلية لكل مُعتمِد.
from odoo import api, fields, models, _


class CareAccessNotifyChannel(models.Model):
    """قناة الإشعار لكل نوع اعتماد — إعداد الإدارة (على مستوى الشركة)."""
    _name = 'care.access.notify.channel'
    _description = 'قناة إشعار نوع اعتماد'
    _order = 'sequence, name'
    _rec_name = 'name'

    key = fields.Char(string='المفتاح', required=True, index=True)
    name = fields.Char(string='نوع الاعتماد', required=True)
    icon = fields.Char(string='الأيقونة')
    sequence = fields.Integer(default=10)
    channel = fields.Selection(
        [('push', '🔔 إشعار فوري'), ('email', '📧 بريد إلكتروني'), ('none', '🔕 بلا إشعار')],
        string='القناة', default='push', required=True)
    mandatory = fields.Boolean(
        string='إلزامي (مقفل على المستخدم)',
        help='الإشعار الإلزامي يصل دائمًا ولا يستطيع المستخدم تعطيله من لوحته.')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [('key_company_uniq', 'unique(key, company_id)',
                         'نوع الاعتماد مُعرَّف مسبقًا لهذه الشركة.')]

    @api.model
    def sync_from_registry(self):
        """يملأ/يحدّث القنوات من سجلّ مركز الموافقات (كل نوع اعتماد مرّة)."""
        App = self.env.get('care.approval.center')
        if App is None:
            return 0
        try:
            entries = App.sudo()._entries()
        except Exception:
            return 0
        existing = {c.key: c for c in self.sudo().search([])}
        n = 0
        seq = 10
        for e in entries:
            seq += 1
            key = e.get('key')
            if not key:
                continue
            vals = {'name': e.get('module') or key, 'icon': e.get('icon') or '🔔', 'sequence': seq}
            if key in existing:
                # لا نلمس channel/mandatory التي ضبطها الأدمن — نحدّث الاسم/الأيقونة فقط
                existing[key].sudo().write({'name': vals['name'], 'icon': vals['icon']})
            else:
                vals['key'] = key
                self.sudo().create(vals)
                n += 1
        return n

    # ---------- القناة الفعلية لمستخدم ----------
    @api.model
    def effective(self, user, key):
        """القناة الفعلية لهذا المستخدم ونوع الاعتماد: 'push' / 'email' / 'none'.
        الإلزامي يتجاوز تعطيل المستخدم."""
        ch = self.sudo().search([('key', '=', key)], limit=1)
        if not ch:
            return 'push'  # الافتراضي عند غياب الإعداد
        if ch.channel == 'none':
            return 'none'
        if ch.mandatory:
            return ch.channel
        # تفضيل المستخدم (تعطيل من ملفه الشخصي) — m2m على res.users، مع دعم opt-out القديم
        u = user if hasattr(user, '_name') else self.env['res.users'].sudo().browse(int(user))
        if 'notify_disabled_ids' in u._fields and ch.id in u.sudo().notify_disabled_ids.ids:
            return 'none'
        off = self.env['care.access.notify.optout'].sudo().search_count(
            [('user_id', '=', u.id), ('key', '=', key)])
        return 'none' if off else ch.channel

    @api.model
    def split_recipients(self, users, key):
        """يقسّم المستخدمين إلى (push, email) حسب قناتهم الفعلية؛ من قناته 'none' يُستبعد."""
        push, email = self.env['res.users'], self.env['res.users']
        for u in users:
            c = self.effective(u, key)
            if c == 'push':
                push |= u
            elif c == 'email':
                email |= u
        return push, email


class CareAccessNotifyOptout(models.Model):
    """تعطيل المستخدم لنوع إشعار غير إلزامي (من لوحته)."""
    _name = 'care.access.notify.optout'
    _description = 'تعطيل إشعار (تفضيل المستخدم)'

    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', index=True,
                              default=lambda s: s.env.user)
    key = fields.Char(string='نوع الاعتماد', required=True, index=True)

    _sql_constraints = [('user_key_uniq', 'unique(user_id, key)', 'مُعطَّل مسبقًا.')]
