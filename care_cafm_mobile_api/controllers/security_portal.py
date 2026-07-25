# -*- coding: utf-8 -*-
"""بورتال الويب لسجل البثّ الأمني — صفحة احترافية تعرض كل البثوث المنتهية على
مواقع العميل مع تسجيلاتها وإمكانية إعادة تشغيلها داخل البورتال (مشغّل Cloudflare
المضمّن). يعيد استخدام نفس منطق النطاق الخاص بواجهة تطبيق العميل حتى لا يرى
العميل إلا بثوث مواقعه هو."""
from odoo.http import request, route

from .security_client_api import SecurityClientApi


class SecurityBroadcastsPortal(SecurityClientApi):

    def _portal_sessions(self, env, limit=100):
        """جلسات البثّ المنتهية الموجَّهة للعميل على مواقعه."""
        if 'care.stream.session' not in env or 'security.premise' not in env:
            return env['care.stream.session'].sudo().browse() if 'care.stream.session' in env else []
        pids, _cids = self._scope(env)
        sess = env['care.stream.session'].sudo().search(
            [('state', '=', 'ended'), ('kind', '=', 'main'),
             ('incident_id', 'in', self._premise_incident_ids(env, pids)),
             ('audience', 'in', ('all', 'client'))], order='id desc', limit=limit)
        # جلب التسجيلات الكسول لِمَن لم تُجلب بعد
        for s in sess:
            if not s.recording_url:
                try:
                    s._fetch_recording()
                except Exception:
                    pass
        return sess

    @route(['/my/security/broadcasts'], type='http', auth='user', website=True)
    def portal_broadcasts(self, **kw):
        env = request.env
        sess = self._portal_sessions(env)
        rows = []
        for s in sess:
            dur = int((s.ended_at - s.started_at).total_seconds()) if (s.started_at and s.ended_at) else 0
            h, m, sec = dur // 3600, (dur % 3600) // 60, dur % 60
            dur_txt = ('%d:%02d:%02d' % (h, m, sec)) if h else ('%d:%02d' % (m, sec))
            iframe = (s.recording_url or '').replace('/manifest/video.m3u8', '/iframe')
            rows.append({
                'id': s.id, 'guard': s.guard_name or '—', 'premise': s.premise_name or '—',
                'started': str(s.started_at or '')[:16], 'dur': dur_txt,
                'peak': s.peak_viewers or 0, 'total': s.total_viewers or 0,
                'has_rec': bool(s.recording_url), 'iframe': iframe,
                'thumb': s.recording_thumbnail or '',
            })
        return request.render('care_cafm_mobile_api.portal_broadcasts', {
            'rows': rows,
            'count': len(rows),
            'rec_count': sum(1 for r in rows if r['has_rec']),
        })
