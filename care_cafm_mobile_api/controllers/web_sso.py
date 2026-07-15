# -*- coding: utf-8 -*-
"""Seamless SSO from the mobile app into the full Odoo web backend.

The app opens /api/v1/web/sso?token=<mobile_token> in a WebView; we resolve the
mobile token to its user and establish a real Odoo web session for that user,
then redirect to /web (or a given internal path). Odoo's own groups still gate
what the user sees — internal users get the backend, portal users the portal."""
from odoo.http import request, Controller, route


class WebSso(Controller):

    @route('/api/v1/web/sso', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def web_sso(self, token=None, redirect=None, **kw):
        tok = token or request.httprequest.args.get('token')
        user = request.env['care.cafm.mobile.token'].sudo().resolve(tok) if tok else None
        if not user:
            return request.redirect('/web/login')
        # establish a genuine web session for this user
        request.session.uid = user.id
        request.session.login = user.login
        request.session.session_token = user._compute_session_token(request.session.sid)
        try:
            request.session.context = dict(user.sudo().context_get() or {})
        except Exception:
            request.session.context = {}
        # only allow internal redirect targets (no open redirect)
        target = redirect or '/web'
        if not target.startswith('/'):
            target = '/web'
        return request.redirect(target)
