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
    # ===== القنوات الثلاث المستقلّة (يمكن تفعيل أكثر من واحدة) =====
    ch_app = fields.Boolean(string='📱 إشعار التطبيق', default=True,
                            help='إشعار فوري (Push) على تطبيق الموبايل.')
    ch_odoo = fields.Boolean(string='🔔 إشعار داخل أودو', default=True,
                             help='إشعار في صندوق الوارد داخل أودو (الجرس).')
    ch_email = fields.Boolean(string='📧 بريد إلكتروني', default=True,
                              help='رسالة بريد إلكتروني.')
    channels_label = fields.Char(string='القنوات', compute='_compute_channels_label')
    mandatory = fields.Boolean(
        string='إلزامي (مقفل على المستخدم)',
        help='الإشعار الإلزامي يصل دائمًا ولا يستطيع المستخدم تعطيله من لوحته.')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('ch_app', 'ch_odoo', 'ch_email')
    def _compute_channels_label(self):
        for c in self:
            parts = []
            if c.ch_app:
                parts.append('📱 تطبيق')
            if c.ch_odoo:
                parts.append('🔔 أودو')
            if c.ch_email:
                parts.append('📧 بريد')
            c.channels_label = ' · '.join(parts) or '🔕 بلا'

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

    # ---------- القنوات الفعّالة لمستخدم ----------
    @api.model
    def channels_for(self, user, key):
        """مجموعة قنوات التسليم الفعّالة لهذا المستخدم ونوع الاعتماد ⊆ {'app','odoo','email'}.
        الإلزامي يتجاوز تعطيل المستخدم؛ تعطيل المستخدم يُلغي كل القنوات."""
        ch = self.sudo().search([('key', '=', key)], limit=1)
        if not ch:
            return {'app', 'odoo'}  # الافتراضي عند غياب الإعداد
        chans = set()
        if ch.ch_app:
            chans.add('app')
        if ch.ch_odoo:
            chans.add('odoo')
        if ch.ch_email:
            chans.add('email')
        if not chans:
            return set()
        if ch.mandatory:
            return chans  # الإلزامي: كل قنوات الإدارة (لا يُعطّلها المستخدم)
        u = user if hasattr(user, '_name') else self.env['res.users'].sudo().browse(int(user))
        pref = self.env['care.user.notify.pref'].sudo().search(
            [('user_id', '=', u.id), ('channel_id', '=', ch.id)], limit=1)
        if not pref:
            return chans  # بلا تفضيل = كل قنوات الإدارة
        user_set = set()
        if pref.use_app:
            user_set.add('app')
        if pref.use_odoo:
            user_set.add('odoo')
        if pref.use_email:
            user_set.add('email')
        return chans & user_set  # المتاح من الإدارة ويريده المستخدم

    @api.model
    def split_recipients(self, users, key):
        """يقسّم المستخدمين حسب القناة: (app, odoo, email) — كلٌّ قد يظهر في أكثر من قناة."""
        app, odoo, email = self.env['res.users'], self.env['res.users'], self.env['res.users']
        for u in users:
            ch = self.channels_for(u, key)
            if 'app' in ch:
                app |= u
            if 'odoo' in ch:
                odoo |= u
            if 'email' in ch:
                email |= u
        return app, odoo, email


class CareUserNotifyPref(models.Model):
    """تفضيل إشعار المستخدم لنوع اعتماد يصله (يظهر في «إشعاراتي» بملفه)."""
    _name = 'care.user.notify.pref'
    _description = 'تفضيل إشعار المستخدم'
    _order = 'channel_name'

    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', index=True)
    channel_id = fields.Many2one('care.access.notify.channel', required=True, ondelete='cascade')
    channel_name = fields.Char(related='channel_id.name', string='نوع الاعتماد', store=True)
    channel_icon = fields.Char(related='channel_id.icon', string='الأيقونة')
    mandatory = fields.Boolean(related='channel_id.mandatory', string='إلزامي')
    # قنوات المستخدم — مُفعّلة افتراضيًّا، يُلغي أيًّا منها (عدا الإلزامي)
    use_app = fields.Boolean(string='📱 تطبيق', default=True)
    use_odoo = fields.Boolean(string='🔔 أودو', default=True)
    use_email = fields.Boolean(string='📧 بريد', default=True)

    _sql_constraints = [('user_channel_uniq', 'unique(user_id, channel_id)', 'مُعرَّف مسبقًا.')]
