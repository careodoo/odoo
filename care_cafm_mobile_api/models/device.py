# -*- coding: utf-8 -*-
"""Device registry + Firebase Cloud Messaging (HTTP v1) sender.

Every app install registers its FCM device token here (per user). When an
in-app notification is created we also fan it out to that user's devices so the
phone shows an OS push even when the app is closed.

Configuration (Settings ▸ Technical ▸ System Parameters):
  * ``care.fcm.credentials`` — the full service-account JSON (one line) from the
    Firebase project (Project settings ▸ Service accounts ▸ Generate key).
No credential ⇒ the sender logs a debug line and no-ops (in-app inbox still works).
"""
import json
import logging
import time

import requests

from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

_TOKEN_URI = 'https://oauth2.googleapis.com/token'
_FCM_SCOPE = 'https://www.googleapis.com/auth/firebase.messaging'
_FCM_SEND = 'https://fcm.googleapis.com/v1/projects/%s/messages:send'


class CafmDevice(models.Model):
    _name = 'care.cafm.device'
    _description = 'Mobile Device (push token)'
    _order = 'write_date desc'
    _sql_constraints = [('token_uniq', 'unique(token)', 'رمز الجهاز مسجّل مسبقًا.')]

    user_id = fields.Many2one('res.users', string='المستخدم', required=True,
                              ondelete='cascade', index=True)
    token = fields.Char(string='رمز الجهاز (FCM)', required=True, index=True)
    platform = fields.Selection([('android', 'Android'), ('ios', 'iOS'), ('web', 'Web')],
                                string='المنصّة', default='android')
    device_name = fields.Char(string='اسم الجهاز')
    app_version = fields.Char(string='إصدار التطبيق', index=True,
                              help='النسخة المثبَّتة على هذا الجهاز — تكشف من لم يحدّث بعد.')
    last_seen = fields.Datetime(string='آخر ظهور', index=True)
    online = fields.Boolean(string='نشط مؤخرًا', compute='_compute_online', search='_search_online')
    active = fields.Boolean(default=True)

    def _compute_online(self):
        limit = fields.Datetime.now() - timedelta(days=7)
        for d in self:
            d.online = bool(d.last_seen and d.last_seen >= limit)

    def _search_online(self, operator, value):
        limit = fields.Datetime.now() - timedelta(days=7)
        op = '>=' if (operator == '=') == bool(value) else '<'
        return [('last_seen', op, limit)]

    @api.model
    def register(self, user, token, platform='android', device_name=None, app_version=None):
        """Upsert a device token for a user (idempotent)."""
        if not token:
            return self.browse()
        dev = self.sudo().search([('token', '=', token)], limit=1)
        vals = {'user_id': user.id, 'platform': platform or 'android',
                'device_name': device_name, 'active': True,
                'last_seen': fields.Datetime.now()}
        if app_version:
            vals['app_version'] = app_version
        if dev:
            dev.write(vals)
        else:
            # سباق تزامن: قد يُنشئ طلبٌ متزامن نفس الرمز بين البحث والإنشاء
            # (التطبيق يسجّل عند البدء وعند الدخول) → INSERT يخالف قيد الرمز الفريد.
            # نحمي بـ savepoint ونعيد البحث/التحديث بدل تعطّل المعاملة كاملة.
            try:
                with self.env.cr.savepoint():
                    dev = self.sudo().create(dict(vals, token=token))
            except Exception:
                dev = self.sudo().search([('token', '=', token)], limit=1)
                if dev:
                    dev.write(vals)
        return dev

    # ---- FCM HTTP v1 ------------------------------------------------------
    def _fcm_credentials(self):
        raw = self.env['ir.config_parameter'].sudo().get_param('care.fcm.credentials')
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            _logger.warning('care.fcm.credentials is not valid JSON')
            return None

    def _fcm_access_token(self, creds):
        """Mint (and cache) a short-lived OAuth2 access token from the service
        account, signing a JWT assertion with PyJWT — no google-auth needed."""
        import jwt  # PyJWT, bundled with Odoo
        ICP = self.env['ir.config_parameter'].sudo()
        cached = ICP.get_param('care.fcm.access_token')
        exp = float(ICP.get_param('care.fcm.access_token_exp') or 0)
        if cached and exp - 60 > time.time():
            return cached
        now = int(time.time())
        assertion = jwt.encode({
            'iss': creds['client_email'], 'scope': _FCM_SCOPE, 'aud': _TOKEN_URI,
            'iat': now, 'exp': now + 3600,
        }, creds['private_key'], algorithm='RS256')
        resp = requests.post(_TOKEN_URI, data={
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion': assertion,
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        tok = data['access_token']
        ICP.set_param('care.fcm.access_token', tok)
        ICP.set_param('care.fcm.access_token_exp', str(now + int(data.get('expires_in', 3600))))
        return tok

    @api.model
    def send_to_users(self, users, title, body=None, data=None):
        """Send a push to every active device of the given users. Safe no-op if
        FCM isn't configured. Never raises into the caller."""
        try:
            creds = self._fcm_credentials()
            if not creds:
                _logger.debug('FCM not configured — skipping device push for %s', title)
                return False
            devices = self.sudo().search([('user_id', 'in', users.ids), ('active', '=', True)])
            if not devices:
                return False
            token = self._fcm_access_token(creds)
            url = _FCM_SEND % creds['project_id']
            headers = {'Authorization': 'Bearer %s' % token, 'Content-Type': 'application/json'}
            payload_data = {k: str(v) for k, v in (data or {}).items()}
            # إشعارات الطوارئ (alert) تُوجَّه لقناة الاستغاثة بالنغمة المميّزة
            is_alert = (data or {}).get('ntype') == 'alert'
            and_notif = {'sound': 'sos_alert', 'channel_id': 'care_sos'} if is_alert else {'sound': 'default'}
            aps_sound = 'sos_alert.caf' if is_alert else 'default'
            sent, dead = 0, self.browse()
            for dev in devices:
                msg = {'message': {
                    'token': dev.token,
                    'notification': {'title': title, 'body': body or ''},
                    'data': payload_data,
                    'android': {'priority': 'high', 'notification': and_notif},
                    'apns': {'payload': {'aps': {'sound': aps_sound}}},
                }}
                r = requests.post(url, headers=headers, data=json.dumps(msg), timeout=15)
                if r.status_code == 200:
                    sent += 1
                elif r.status_code in (404, 400) and 'UNREGISTERED' in r.text:
                    dead |= dev  # stale token → deactivate
                else:
                    _logger.warning('FCM send failed (%s): %s', r.status_code, r.text[:200])
            if dead:
                dead.write({'active': False})
            return sent
        except Exception as e:
            _logger.warning('FCM push error: %s', e)
            return False
