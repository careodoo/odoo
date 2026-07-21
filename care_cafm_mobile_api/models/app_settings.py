# -*- coding: utf-8 -*-
"""App control centre settings.

Everything here used to live in raw system parameters — the FCM service account
had to be pasted over a shell. This puts it behind a real screen, with a test
button that proves the key works instead of leaving you to guess.
"""
import json

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CareAppSettings(models.Model):
    _name = 'care.app.settings'
    _description = 'إعدادات التطبيق'

    name = fields.Char(default='إعدادات التطبيق', readonly=True)

    # ---- push -------------------------------------------------------------
    fcm_credentials = fields.Text(
        string='مفتاح Firebase (Service Account JSON)',
        help='من Firebase Console ← Project settings ← Service accounts ← Generate new private key. '
             'الصق محتوى الملف كاملًا.')
    fcm_project_id = fields.Char(string='مشروع Firebase', compute='_compute_fcm', store=False)
    fcm_ready = fields.Boolean(string='الإشعارات جاهزة', compute='_compute_fcm', store=False)
    fcm_status = fields.Char(string='الحالة', compute='_compute_fcm', store=False)

    # ---- version gating ---------------------------------------------------
    min_version = fields.Char(
        string='أقل إصدار مسموح', help='مثال: 2.14.0 — من عنده أقدم منه يُطالَب بالتحديث.')
    force_update = fields.Boolean(
        string='إلزام التحديث',
        help='إن فُعّل، لا يستطيع من هو دون «أقل إصدار» استخدام التطبيق حتى يحدّث.')
    update_message = fields.Char(string='رسالة التحديث', default='يتوفّر إصدار جديد من التطبيق')
    android_url = fields.Char(string='رابط تحميل أندرويد',
                              default='https://ecare.care-kw.com/care_hr/static/download/care-cafm.apk')
    ios_url = fields.Char(string='رابط App Store')

    # ---- worker file visibility -------------------------------------------
    show_worker_attendance = fields.Boolean(
        string='إظهار الحضور والانصراف للعامل', default=True,
        help='عند التعطيل يُخفى سجل الحضور والانصراف من ملف العامل في التطبيق.')
    show_worker_documents = fields.Boolean(
        string='إظهار بيانات الإقامة والوثائق', default=True,
        help='عند التعطيل تُخفى تواريخ الإقامة والتصاريح من ملف العامل.')

    # ---- media server -----------------------------------------------------
    # Two selectable strategies, chosen later from this same screen:
    #  · local   → serve every image/video from this Odoo server (default)
    #  · cdn     → keep files here but hand the app/portal a different base URL
    #              (a CDN / reverse-proxy in front of Odoo) — no data migration
    #  · offload → store the attachment BYTES themselves on an external location
    #              (Odoo's native ir_attachment.location, e.g. a mount or S3 URI)
    media_mode = fields.Selection([
        ('local', 'على هذا السيرفر (افتراضي)'),
        ('cdn', 'رابط سيرفر وسائط منفصل (CDN / إعادة توجيه)'),
        ('offload', 'تخزين خارجي كامل للملفات'),
    ], string='مصدر الوسائط', default='local',
        help='يحدّد من أين يجلب التطبيق والبورتال الصور والفيديوهات.')
    media_cdn_base = fields.Char(
        string='رابط سيرفر الوسائط (CDN)',
        help='مثال: https://media.care-kw.com — تُبنى كل روابط الصور/الفيديو من هذا '
             'الرابط بدل رابط الخادم. اتركه فارغًا للوضع المحلي.')
    media_offload_location = fields.Char(
        string='موقع التخزين الخارجي',
        help='قيمة ir_attachment.location في Odoo — مثل file:///mnt/media أو رابط '
             'تخزين S3 حسب الوحدة المثبّتة. تُطبَّق على المرفقات الجديدة.')
    media_status = fields.Char(string='الحالة', compute='_compute_media_status')

    @api.depends('media_mode', 'media_cdn_base', 'media_offload_location')
    def _compute_media_status(self):
        for s in self:
            if s.media_mode == 'cdn':
                s.media_status = ('✅ الوسائط من: %s' % s.media_cdn_base) if s.media_cdn_base \
                    else '⚠ اختر وضع CDN لكن الرابط فارغ — يعمل محليًا'
            elif s.media_mode == 'offload':
                s.media_status = ('✅ تخزين خارجي: %s' % s.media_offload_location) if s.media_offload_location \
                    else '⚠ اختر التخزين الخارجي لكن الموقع فارغ'
            else:
                s.media_status = 'الوسائط تُخدَم من هذا السيرفر'

    # ---- maintenance ------------------------------------------------------
    maintenance = fields.Boolean(string='وضع الصيانة',
                                 help='يعرض للتطبيق رسالة صيانة بدل المحتوى.')
    maintenance_message = fields.Char(string='رسالة الصيانة',
                                      default='النظام تحت الصيانة، نعود إليكم قريبًا')

    # ---- live counters ----------------------------------------------------
    device_count = fields.Integer(string='الأجهزة المسجّلة', compute='_compute_stats')
    online_count = fields.Integer(string='نشطة خلال أسبوع', compute='_compute_stats')
    session_count = fields.Integer(string='الجلسات المفتوحة', compute='_compute_stats')
    outdated_count = fields.Integer(string='أجهزة قديمة', compute='_compute_stats')

    def _compute_fcm(self):
        for s in self:
            raw = s.fcm_credentials or self.env['ir.config_parameter'].sudo().get_param('care.fcm.credentials')
            pid, ok, status = False, False, 'لم يُضبط — الإشعارات معطّلة'
            if raw:
                try:
                    d = json.loads(raw)
                    pid = d.get('project_id')
                    ok = bool(d.get('private_key') and d.get('client_email') and pid)
                    status = 'جاهز ✓' if ok else 'JSON ناقص (يلزم private_key و client_email و project_id)'
                except Exception:
                    status = '❌ النص ليس JSON صالحًا'
            s.fcm_project_id = pid
            s.fcm_ready = ok
            s.fcm_status = status

    def _compute_stats(self):
        D = self.env['care.cafm.device'].sudo()
        T = self.env['care.cafm.mobile.token'].sudo()
        for s in self:
            s.device_count = D.search_count([])
            s.online_count = D.search_count([('online', '=', True)])
            s.session_count = T.search_count([('active', '=', True)])
            s.outdated_count = (D.search_count([('app_version', '!=', s.min_version),
                                                ('app_version', '!=', False)])
                                if s.min_version else 0)

    # ---- singleton --------------------------------------------------------
    @api.model
    def get_settings(self):
        rec = self.search([], limit=1)
        if not rec:
            rec = self.create({})
        return rec

    @api.model
    def open_settings(self):
        rec = self.get_settings()
        return {'type': 'ir.actions.act_window', 'res_model': self._name,
                'view_mode': 'form', 'res_id': rec.id, 'target': 'current',
                'name': _('إعدادات التطبيق')}

    def write(self, vals):
        res = super().write(vals)
        # the API reads the key from the system parameter — keep them in step
        if 'fcm_credentials' in vals:
            raw = (vals.get('fcm_credentials') or '').strip()
            if raw:
                try:
                    json.loads(raw)
                except Exception:
                    raise UserError(_('مفتاح Firebase ليس JSON صالحًا.'))
            self.env['ir.config_parameter'].sudo().set_param('care.fcm.credentials', raw)
            # a new key invalidates the cached OAuth token
            self.env['ir.config_parameter'].sudo().set_param('care.fcm.access_token', '')
            self.env['ir.config_parameter'].sudo().set_param('care.fcm.access_token_exp', '0')
        # media server — mirror to fast, cached config params that _abs() reads,
        # and drive Odoo's native external-storage hook for the offload mode.
        P = self.env['ir.config_parameter'].sudo()
        if 'media_mode' in vals:
            P.set_param('care.media.mode', vals.get('media_mode') or 'local')
        if 'media_cdn_base' in vals:
            P.set_param('care.media.cdn_base', (vals.get('media_cdn_base') or '').strip().rstrip('/'))
        if 'media_offload_location' in vals or 'media_mode' in vals:
            rec = self[:1]
            if rec.media_mode == 'offload' and rec.media_offload_location:
                P.set_param('ir_attachment.location', rec.media_offload_location.strip())
            elif 'media_mode' in vals and vals.get('media_mode') != 'offload':
                # leaving offload → stop forcing an external location for new files
                P.set_param('ir_attachment.location', '')
        return res

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        P = self.env['ir.config_parameter'].sudo()
        if 'fcm_credentials' in fields_list:
            vals['fcm_credentials'] = P.get_param('care.fcm.credentials')
        if 'media_mode' in fields_list:
            vals['media_mode'] = P.get_param('care.media.mode', 'local')
        if 'media_cdn_base' in fields_list:
            vals['media_cdn_base'] = P.get_param('care.media.cdn_base', '')
        if 'media_offload_location' in fields_list:
            vals['media_offload_location'] = P.get_param('ir_attachment.location', '')
        return vals

    # ---- actions ----------------------------------------------------------
    def action_test_fcm(self):
        """Prove the key really authenticates with Google — no guessing."""
        self.ensure_one()
        D = self.env['care.cafm.device'].sudo()
        creds = D._fcm_credentials()
        if not creds:
            raise UserError(_('لم يُضبط مفتاح Firebase بعد.'))
        try:
            token = D._fcm_access_token(creds)
        except Exception as e:
            raise UserError(_('❌ فشل الاتصال بـ Google:\n%s') % e)
        if not token:
            raise UserError(_('❌ تعذّر إصدار رمز الدخول من Google.'))
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'type': 'success', 'sticky': False,
                           'title': _('Firebase متصل ✓'),
                           'message': _('المشروع %s — Google قبلت المفتاح وأصدرت رمز دخول.')
                                      % creds.get('project_id')}}

    def action_push_test_me(self):
        """Send a real push to my own devices."""
        self.ensure_one()
        devs = self.env['care.cafm.device'].sudo().search(
            [('user_id', '=', self.env.user.id), ('active', '=', True)])
        if not devs:
            raise UserError(_('لا يوجد جهاز مسجّل لحسابك. ثبّت التطبيق وسجّل دخولك أولًا.'))
        self.env['care.cafm.notification'].sudo().push(
            self.env.user, _('🔔 اختبار'), _('وصلك هذا الإشعار — الإشعارات تعمل.'), ntype='info')
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'type': 'success', 'sticky': False, 'title': _('أُرسل'),
                           'message': _('أُرسل إلى %s جهاز — تحقّق من هاتفك.') % len(devs)}}

    def action_view_devices(self):
        return {'type': 'ir.actions.act_window', 'name': _('الأجهزة'),
                'res_model': 'care.cafm.device', 'view_mode': 'tree,form'}

    def action_view_sessions(self):
        return {'type': 'ir.actions.act_window', 'name': _('الجلسات'),
                'res_model': 'care.cafm.mobile.token', 'view_mode': 'tree,form'}
