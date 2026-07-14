# -*- coding: utf-8 -*-
"""Keeps the CAFM mobile launcher's "full security app" entry working, but now it
opens the REAL Security Manager backend (dashboard) instead of a re-implementation."""

from odoo import http
from odoo.http import request


class CafmSecurityBridge(http.Controller):

    @http.route('/cafm/m/sec', type='http', auth='user', website=False)
    def security_app(self, **kw):
        # Open the genuine Security Manager dashboard (client action).
        return request.redirect('/web#action=security_management.action_security_dashboard')
