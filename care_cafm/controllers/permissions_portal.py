# -*- coding: utf-8 -*-
"""What this client may do, shown to the client.

Permissions were invisible: a button either worked or returned a refusal, and
nobody could see the shape of what they held or ask for more. This page states
it plainly, and lets an account holder request a capability rather than guess
why something is missing.
"""
from markupsafe import Markup

from odoo import http, _
from odoo.http import request

from .main import _shell, esc, _csrf
from ..models.client_permission import PERMISSIONS, GROUPS

ACCENT = '#0891b2'


class PermissionsPortal(http.Controller):

    def _client(self):
        """Membership first — a client contact usually has their own partner."""
        env = request.env
        C = env['care.cafm.client'].sudo()
        by_member = C.search([('user_ids', 'in', env.user.id)], limit=1)
        if by_member:
            return by_member
        p = env.user.partner_id.commercial_partner_id or env.user.partner_id
        return C.search([('partner_id', '=', p.id)], limit=1) if p else C.browse()

    @http.route('/cafm/m/permissions', type='http', auth='user', website=False)
    def permissions(self, **kw):
        env = request.env
        client = self._client()
        is_staff = (env.user.has_group('base.group_system')
                    or env.user.has_group('base.group_erp_manager'))
        if not client and not is_staff:
            return _shell('صلاحياتي', Markup(
                '<div class="card"><div class="muted">حسابك غير مرتبط بعميل.</div></div>'),
                accent=ACCENT)

        granted = set(c for c, _l, _h, _d, _g in PERMISSIONS) if is_staff else client.granted_codes()
        body = Markup(
            '<div class="card"><div class="h4">🔐 %s</div>'
            '<div class="muted" style="margin-top:5px">'
            'هذه الصلاحيات تحدّد ما يستطيع مستخدمو حسابكم فعله داخل النظام. '
            'كل صلاحية مستقلّة — ولا تُمنح إلا بموافقة فريق CARE.</div>'
            '<div class="kpi" style="margin-top:11px">'
            '<div><div class="n" style="color:#37c98a">%s</div><div class="l">ممنوحة</div></div>'
            '<div><div class="n">%s</div><div class="l">غير ممنوحة</div></div>'
            '</div></div>'
        ) % (esc(client.name if client else 'فريق CARE'),
             len(granted), len(PERMISSIONS) - len(granted))

        by_group = {}
        for code, label, help_, default, group in PERMISSIONS:
            by_group.setdefault(group, []).append((code, label, help_))
        for group, rows in by_group.items():
            body += Markup('<h3 style="margin:17px 0 9px">%s</h3>') % esc(GROUPS.get(group, group))
            for code, label, help_ in rows:
                on = code in granted
                pill = (Markup('<span class="pill ok">✔ ممنوحة</span>') if on
                        else Markup('<span class="pill" style="background:#ffffff;color:#71809a">'
                                    '— غير ممنوحة</span>'))
                ask = Markup('')
                if not on and client:
                    ask = Markup(
                        '<form method="post" action="/cafm/m/permissions/request" '
                        'style="margin-top:8px">%s'
                        '<input type="hidden" name="code" value="%s"/>'
                        '<button class="btn g">اطلب هذه الصلاحية</button></form>') % (_csrf(), code)
                body += Markup(
                    '<div class="card" style="%s"><div class="row"><div class="h4">%s</div>%s</div>'
                    '<div class="muted" style="margin-top:4px">%s</div>%s</div>'
                ) % (Markup('' if on else 'opacity:.72'), esc(label), pill, esc(help_), ask)
        return _shell('صلاحياتي', body, accent=ACCENT)

    @http.route('/cafm/m/permissions/request', type='http', auth='user',
                methods=['POST'], website=False, csrf=True)
    def request_permission(self, **post):
        """Ask for a capability. This never grants anything — it raises the
        request with CARE, because a client granting themselves permissions
        would make the whole matrix decorative."""
        env = request.env
        code = post.get('code')
        client = self._client()
        valid = {c: l for c, l, _h, _d, _g in PERMISSIONS}
        if not client or code not in valid:
            return request.redirect('/cafm/m/permissions')
        body = _('طلب صلاحية «%(perm)s» من %(user)s (%(client)s).') % {
            'perm': valid[code], 'user': env.user.name, 'client': client.name}
        try:
            client.message_post(body=Markup('<p>%s</p>') % esc(body),
                                message_type='comment',
                                author_id=env.user.partner_id.id)
        except Exception:
            pass
        # tell whoever looks after this account
        try:
            managers = env['res.users'].sudo().search(
                [('groups_id', 'in', env.ref('base.group_erp_manager').id)], limit=20)
            if managers and 'care.cafm.notification' in env:
                env['care.cafm.notification'].sudo().push(
                    managers, _('🔐 طلب صلاحية جديد'), body, ntype='task',
                    action_url='/cafm/m/permissions')
        except Exception:
            pass
        done = Markup(
            '<div class="card"><div class="big" style="color:#37c98a">✔ أُرسل الطلب</div>'
            '<p class="muted">%s<br/>سيتواصل معكم فريق CARE.</p></div>'
            '<a class="btn g" href="/cafm/m/permissions">رجوع للصلاحيات</a>') % esc(body)
        return _shell('تم الإرسال', done, accent=ACCENT, back='/cafm/m/permissions')
