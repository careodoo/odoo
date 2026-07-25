# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StreamProvider(models.Model):
    """مزوّد بث خارجي (خادم بعيد عن Odoo). المدير يضيف عدة خدمات (RTMP/HLS/…)
    ويُعدّها بالكامل هنا؛ Odoo يخزّن الإعدادات ويولّد روابط الإدخال والمشاهدة
    من القوالب، بينما يجري البث الفعلي على خادم المزوّد."""
    _name = 'care.stream.provider'
    _description = 'مزوّد بث مباشر'
    _order = 'sequence, id'

    name = fields.Char(string='الاسم', required=True)
    sequence = fields.Integer(string='الترتيب', default=10)
    active = fields.Boolean(string='مفعّل', default=True)
    provider_type = fields.Selection([
        ('rtmp', 'RTMP/HLS عام'),
        ('cloudflare', 'Cloudflare Stream'),
        ('mux', 'Mux'),
        ('livekit', 'LiveKit'),
        ('agora', 'Agora'),
        ('custom', 'مخصّص'),
    ], string='نوع الخدمة', required=True, default='rtmp')

    # بيانات الاعتماد (تُخزَّن في الباك ايند فقط، لا تُرسل للتطبيق إلا عند الحاجة)
    app_id = fields.Char(string='App ID / Account')
    api_key = fields.Char(string='مفتاح API')
    api_secret = fields.Char(string='سرّ API')
    base_url = fields.Char(string='عنوان الخادم', help='مثال: rtmp://live.example.com/app')

    # قوالب الروابط: {channel} يُستبدل باسم القناة، {key} بمفتاح البث
    ingest_url_template = fields.Char(
        string='قالب رابط الإدخال (البث)',
        help='يبثّ إليه الحارس. مثال: rtmp://live.example.com/app/{channel}?key={key}')
    playback_url_template = fields.Char(
        string='قالب رابط المشاهدة (HLS)',
        help='يفتحه المشاهدون. مثال: https://live.example.com/hls/{channel}.m3u8')
    requires_token = fields.Boolean(string='يتطلب رمزاً', default=False,
                                    help='بعض الخدمات (Agora/LiveKit) تحتاج توليد رمز من الخادم')

    # تكامل Cloudflare API: إنشاء Live Input ديناميكي لكل بثّ — يتيح بثوثاً
    # متعددة متزامنة ومشاركة (co-host) حقيقية (كل مشارك قناته الخاصة).
    dynamic_input = fields.Boolean(
        string='قناة لكل بثّ (Cloudflare API)', default=False,
        help='عند التفعيل يُنشئ Odoo Live Input جديداً لكل بثّ عبر Cloudflare API '
             '(يتيح بثوثاً متزامنة ومشاركة co-host). يتطلب Account ID + API Token.')
    cf_account_id = fields.Char(string='Cloudflare Account ID')
    cf_api_token = fields.Char(string='Cloudflare API Token')
    cf_recording = fields.Selection([
        ('off', 'بلا تسجيل'),
        ('automatic', 'تسجيل تلقائي'),
    ], string='تسجيل Cloudflare', default='off')
    # قوالب WebRTC (بثّ داخل التطبيق بزمن منخفض عبر WHIP/WHEP — مثل Cloudflare)
    whip_url_template = fields.Char(
        string='قالب رابط النشر WebRTC (WHIP)',
        help='ينشر إليه الحارس من داخل التطبيق. Cloudflare: '
             'https://customer-CODE.cloudflarestream.com/SECRET_KEY/webRTC/publish')
    whep_url_template = fields.Char(
        string='قالب رابط المشاهدة WebRTC (WHEP)',
        help='يشاهد به العميل/الفريق داخل التطبيق. Cloudflare: '
             'https://customer-CODE.cloudflarestream.com/INPUT_UID/webRTC/play')

    notes = fields.Text(string='ملاحظات')

    def _fill_tpl(self, tpl, channel='', key=''):
        """تعبئة قالب رابط بالمتغيّرات المتاحة."""
        if not tpl:
            return ''
        return (tpl.replace('{channel}', channel or '')
                   .replace('{key}', key or '')
                   .replace('{app_id}', self.app_id or ''))

    def _build_urls(self, channel, key=''):
        """توليد كل روابط القناة (RTMP + WebRTC) من القوالب."""
        self.ensure_one()
        return {
            'ingest_url': self._fill_tpl(self.ingest_url_template, channel, key),
            'playback_url': self._fill_tpl(self.playback_url_template, channel, key),
            'whip_url': self._fill_tpl(self.whip_url_template, channel, key),
            'whep_url': self._fill_tpl(self.whep_url_template, channel, key),
        }

    @property
    def supports_webrtc(self):
        self.ensure_one()
        return bool(self.whip_url_template) or (self.provider_type == 'cloudflare' and self.dynamic_input)

    def _cf_create_input(self, name):
        """ينشئ Live Input جديداً عبر Cloudflare API ويُرجع روابطه (WHIP/WHEP/
        RTMP/HLS) + الـ UID. يُرجع None عند غياب الاعتماد أو فشل الطلب (فيرجع
        النظام تلقائياً للقالب الثابت)."""
        self.ensure_one()
        if not (self.provider_type == 'cloudflare' and self.dynamic_input
                and self.cf_account_id and self.cf_api_token):
            return None
        try:
            import requests
            url = 'https://api.cloudflare.com/client/v4/accounts/%s/stream/live_inputs' % self.cf_account_id
            resp = requests.post(url, timeout=15,
                headers={'Authorization': 'Bearer %s' % self.cf_api_token,
                         'Content-Type': 'application/json'},
                json={'meta': {'name': name[:80]},
                      'recording': {'mode': self.cf_recording or 'off'}})
            if resp.status_code not in (200, 201):
                return None
            res = (resp.json() or {}).get('result') or {}
            uid = res.get('uid')
            if not uid:
                return None
            rtmps = res.get('rtmps') or {}
            webrtc = res.get('webRTC') or {}
            webrtc_play = res.get('webRTCPlayback') or {}
            code = self.app_id or ''  # customer-xxxx
            return {
                'input_uid': uid,
                'ingest_url': '%s%s' % (rtmps.get('url') or '', rtmps.get('streamKey') or ''),
                'whip_url': webrtc.get('url') or '',
                'whep_url': webrtc_play.get('url') or '',
                'playback_url': ('https://%s.cloudflarestream.com/%s/manifest/video.m3u8' % (code, uid))
                                if code and uid else '',
            }
        except Exception:
            return None

    def _cf_delete_input(self, uid):
        """يحذف Live Input عند انتهاء البثّ. لا يُحذف إن كان التسجيل مفعّلاً — لأن
        حذف الـ Input يحذف تسجيلاته (VOD) أيضاً، ونريد الاحتفاظ بها في السجل."""
        self.ensure_one()
        if self.cf_recording == 'automatic':
            return  # نُبقي الـ Input للاحتفاظ بالتسجيل
        if not (uid and self.cf_account_id and self.cf_api_token):
            return
        try:
            import requests
            requests.delete(
                'https://api.cloudflare.com/client/v4/accounts/%s/stream/live_inputs/%s' % (self.cf_account_id, uid),
                headers={'Authorization': 'Bearer %s' % self.cf_api_token}, timeout=10)
        except Exception:
            pass

    def _cf_recordings(self, input_uid):
        """يجلب تسجيلات (VOD) لـ Live Input من Cloudflare — لإعادة التشغيل."""
        self.ensure_one()
        if not (self.cf_account_id and self.cf_api_token and input_uid):
            return []
        try:
            import requests
            url = ('https://api.cloudflare.com/client/v4/accounts/%s/stream/live_inputs/%s/videos'
                   % (self.cf_account_id, input_uid))
            resp = requests.get(url, headers={'Authorization': 'Bearer %s' % self.cf_api_token}, timeout=15)
            if resp.status_code != 200:
                return []
            code = self.app_id or ''
            out = []
            for v in ((resp.json() or {}).get('result') or []):
                uid = v.get('uid')
                if not uid:
                    continue
                out.append({
                    'uid': uid,
                    'playback': 'https://%s.cloudflarestream.com/%s/manifest/video.m3u8' % (code, uid),
                    'thumbnail': 'https://%s.cloudflarestream.com/%s/thumbnails/thumbnail.jpg' % (code, uid),
                    'duration': v.get('duration') or 0.0,
                    'ready': (v.get('status') or {}).get('state') == 'ready',
                })
            return out
        except Exception:
            return []
