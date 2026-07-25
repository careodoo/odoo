# -*- coding: utf-8 -*-
"""جلسة بثّ مباشر واحدة + تتبّع المشاهدين.

سجل تشغيلي يُنشأ عند بدء الحارس البثّ، ويحمل لقطة كاملة عن البثّ (الحارس،
الموقع، العميل، البلاغ، الروابط، الموقع الجغرافي) وقائمة المشاهدين النشطين
لحظياً — حتى تعرض شاشة الحارس «من يشاهد الآن»، وتعرض شاشة العميل بيانات البثّ."""
from odoo import api, fields, models


class StreamSession(models.Model):
    _name = 'care.stream.session'
    _description = 'جلسة بثّ مباشر'
    _order = 'started_at desc, id desc'

    name = fields.Char(string='القناة', required=True, index=True)
    incident_id = fields.Integer(string='رقم البلاغ', index=True)
    provider_id = fields.Many2one('care.stream.provider', string='المزوّد', ondelete='set null')

    # الحارس الباثّ
    guard_user_id = fields.Many2one('res.users', string='الحارس (مستخدم)', ondelete='set null')
    guard_name = fields.Char(string='اسم الحارس')

    # لقطة عن الموقع/العميل وقت البدء (لا تعتمد على بقاء السجلات)
    premise_name = fields.Char(string='الموقع')
    client_name = fields.Char(string='العميل')

    # الروابط المولّدة
    whip_url = fields.Char(string='رابط النشر WebRTC')
    whep_url = fields.Char(string='رابط المشاهدة WebRTC')
    playback_url = fields.Char(string='رابط المشاهدة HLS')
    ingest_url = fields.Char(string='رابط الإدخال RTMP')

    # معرّف Cloudflare Live Input الديناميكي (لحذفه عند الانتهاء)
    cf_input_uid = fields.Char(string='Cloudflare Input UID')

    # التسجيل (VOD) — يُجلب من Cloudflare بعد انتهاء البثّ
    recording_uid = fields.Char(string='معرّف التسجيل')
    recording_url = fields.Char(string='رابط إعادة التشغيل (HLS)')
    recording_thumbnail = fields.Char(string='الصورة المصغّرة')
    recording_duration = fields.Float(string='مدة التسجيل (ث)')
    has_recording = fields.Boolean(string='له تسجيل', compute='_compute_has_recording', store=True)
    recording_embed = fields.Html(string='مشغّل التسجيل', compute='_compute_recording_embed', sanitize=False)

    @api.depends('recording_url')
    def _compute_has_recording(self):
        for s in self:
            s.has_recording = bool(s.recording_url)

    @api.depends('recording_url')
    def _compute_recording_embed(self):
        # مشغّل Cloudflare مضمّن لإعادة التشغيل داخل الباك ايند مباشرةً
        from markupsafe import Markup
        for s in self:
            if s.recording_url:
                iframe = s.recording_url.replace('/manifest/video.m3u8', '/iframe')
                s.recording_embed = Markup(
                    '<div style="position:relative;padding-top:56.25%;background:#000;border-radius:8px;overflow:hidden">'
                    '<iframe src="%s" style="position:absolute;top:0;left:0;width:100%%;height:100%%;border:none" '
                    'allow="accelerometer;gyroscope;autoplay;encrypted-media;picture-in-picture" '
                    'allowfullscreen="true"></iframe></div>' % iframe)
            else:
                s.recording_embed = Markup(
                    '<div style="padding:24px;text-align:center;color:#888;background:#f5f5f5;border-radius:8px">'
                    'لا يوجد تسجيل متاح بعد — اضغط «جلب التسجيل» بعد انتهاء البثّ.</div>')

    def action_fetch_recording(self):
        """زر يدوي لجلب تسجيل البثّ من Cloudflare (VOD)."""
        for s in self:
            s._fetch_recording()
        return True

    # الموقع الجغرافي للبثّ
    latitude = fields.Float(string='خط العرض', digits=(10, 7))
    longitude = fields.Float(string='خط الطول', digits=(10, 7))

    # المشاركة في البثّ (co-host): جلسة فرعية لعضو فريق يبثّ داخل نفس البلاغ،
    # تظهر كصورة سفلية (PiP) في البثّ الرئيسي.
    kind = fields.Selection([
        ('main', 'رئيسي'),
        ('cohost', 'مشارك'),
    ], string='النوع', default='main', index=True)
    parent_id = fields.Many2one('care.stream.session', string='البثّ الرئيسي', ondelete='cascade')
    cohost_ids = fields.One2many('care.stream.session', 'parent_id', string='المشاركون في البثّ')

    message_ids = fields.One2many('care.stream.message', 'session_id', string='الرسائل')

    # الجمهور: من يُشعَر ويرى البثّ (يختاره الحارس عند البدء)
    audience = fields.Selection([
        ('all', 'الكل (الفريق + العميل)'),
        ('client', 'العميل فقط'),
        ('team', 'الفريق فقط'),
    ], string='الجمهور', default='all')

    state = fields.Selection([
        ('live', 'مباشر'),
        ('ended', 'منتهٍ'),
    ], string='الحالة', default='live', index=True)
    started_at = fields.Datetime(string='بدأ في', default=fields.Datetime.now)
    ended_at = fields.Datetime(string='انتهى في')

    viewer_ids = fields.One2many('care.stream.viewer', 'session_id', string='المشاهدون')
    viewer_count = fields.Integer(string='المشاهدون الآن', compute='_compute_viewer_count')
    peak_viewers = fields.Integer(string='ذروة المشاهدين', default=0)
    total_viewers = fields.Integer(string='إجمالي من شاهد', compute='_compute_viewer_count')

    @api.depends('viewer_ids.active')
    def _compute_viewer_count(self):
        for s in self:
            s.viewer_count = len(s.viewer_ids.filtered('active'))
            s.total_viewers = len(s.viewer_ids)

    def _join(self, user):
        """تسجيل انضمام مشاهد (أو إعادة تنشيطه)، وتحديث الذروة."""
        self.ensure_one()
        V = self.env['care.stream.viewer'].sudo()
        v = V.search([('session_id', '=', self.id), ('user_id', '=', user.id)], limit=1)
        if v:
            v.write({'active': True, 'left_at': False})
        else:
            v = V.create({
                'session_id': self.id, 'user_id': user.id,
                'user_name': user.name,
            })
        live = len(self.viewer_ids.filtered('active'))
        if live > (self.peak_viewers or 0):
            self.peak_viewers = live
        return v

    def _leave(self, user):
        self.ensure_one()
        v = self.env['care.stream.viewer'].sudo().search(
            [('session_id', '=', self.id), ('user_id', '=', user.id)], limit=1)
        if v:
            v.write({'active': False, 'left_at': fields.Datetime.now()})

    def _end(self):
        for s in self:
            s.viewer_ids.filtered('active').write({'active': False, 'left_at': fields.Datetime.now()})
            # تنظيف الـ Live Input الديناميكي على Cloudflare (إن وُجد)
            if s.cf_input_uid and s.provider_id:
                s.provider_id._cf_delete_input(s.cf_input_uid)
            s.write({'state': 'ended', 'ended_at': fields.Datetime.now()})

    def _fetch_recording(self):
        """يجلب تسجيل الجلسة (VOD) من Cloudflare إن توفّر ويخزّنه — يُستدعى كسولاً
        عند عرض الأرشيف (المعالجة تستغرق دقائق بعد انتهاء البثّ)."""
        for s in self:
            if s.recording_url or not (s.cf_input_uid and s.provider_id):
                continue
            recs = s.provider_id._cf_recordings(s.cf_input_uid)
            if not recs:
                continue
            ready = [r for r in recs if r.get('ready')] or recs
            r = ready[0]
            s.write({
                'recording_uid': r['uid'], 'recording_url': r['playback'],
                'recording_thumbnail': r['thumbnail'], 'recording_duration': r['duration'],
            })


class StreamViewer(models.Model):
    _name = 'care.stream.viewer'
    _description = 'مشاهد بثّ'
    _order = 'joined_at desc'

    session_id = fields.Many2one('care.stream.session', string='الجلسة', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='المستخدم', ondelete='cascade')
    user_name = fields.Char(string='الاسم')
    joined_at = fields.Datetime(string='انضمّ في', default=fields.Datetime.now)
    left_at = fields.Datetime(string='غادر في')
    active = fields.Boolean(string='يشاهد الآن', default=True)


class StreamMessage(models.Model):
    """رسالة دردشة حيّة على البثّ (بين الفريق والعميل)."""
    _name = 'care.stream.message'
    _description = 'رسالة بثّ'
    _order = 'id asc'

    session_id = fields.Many2one('care.stream.session', string='الجلسة', required=True, ondelete='cascade', index=True)
    incident_id = fields.Integer(string='رقم البلاغ', index=True)
    user_id = fields.Many2one('res.users', string='المرسِل', ondelete='set null')
    user_name = fields.Char(string='الاسم')
    body = fields.Char(string='النص', required=True)
    kind = fields.Selection([
        ('chat', 'رسالة'),
        ('system', 'نظام'),
        ('join', 'انضمام'),
    ], string='النوع', default='chat')
    is_client = fields.Boolean(string='من العميل', default=False)
    created_at = fields.Datetime(string='الوقت', default=fields.Datetime.now, index=True)
