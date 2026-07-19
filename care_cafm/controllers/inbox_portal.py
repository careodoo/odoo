# -*- coding: utf-8 -*-
"""Notifications inbox and support tickets on the web portal.

Both existed only inside the mobile app, which meant a user on a desk terminal
had no way to see what they had been told or to raise a problem. Same data,
same actions, same shell as the rest of the CAFM portal.
"""
from markupsafe import Markup

from odoo import http, _
from odoo.http import request

from .main import _shell, esc

ACCENT = '#4aa8ff'
SUPPORT_ACCENT = '#0ea5a5'

_NTYPE = {'info': 'info', 'task': 'warn', 'warning': 'warn', 'alert': 'crit'}


def _csrf():
    return Markup('<input type="hidden" name="csrf_token" value="%s"/>') % request.csrf_token()


class InboxPortal(http.Controller):

    # ---------------- notifications ----------------
    @http.route('/cafm/m/inbox', type='http', auth='user', website=False)
    def inbox(self, filter='all', **kw):
        env = request.env
        N = env['care.cafm.notification'].sudo()
        dom = [('user_id', '=', env.user.id)]
        if filter == 'unread':
            dom.append(('is_read', '=', False))
        notifs = N.search(dom, limit=100)
        unread = N.search_count([('user_id', '=', env.user.id), ('is_read', '=', False)])

        body = Markup(
            '<div class="kpi"><div><div class="n">%s</div><div class="l">غير مقروءة</div></div>'
            '<div><div class="n">%s</div><div class="l">الإجمالي</div></div></div>'
        ) % (unread, N.search_count([('user_id', '=', env.user.id)]))

        body += Markup('<div style="display:flex;gap:7px;margin:15px 0 11px">')
        for key, label in (('all', 'الكل'), ('unread', 'غير المقروءة')):
            sel = ('background:%s;color:#ffffff' % ACCENT) if key == filter else 'background:#ffffff;color:#71809a'
            body += Markup('<a href="/cafm/m/inbox?filter=%s" class="pill" style="%s;padding:7px 12px">%s</a>') % (
                key, Markup(sel), esc(label))
        if unread:
            body += Markup(
                '<form method="post" action="/cafm/m/inbox/read-all" style="margin:0">%s'
                '<button class="pill" style="background:#ffffff;color:#14202b;border:none;padding:7px 12px;'
                'cursor:pointer;font-family:inherit">تعليم الكل كمقروء</button></form>') % _csrf()
        body += Markup('</div>')

        if not notifs:
            body += Markup('<div class="card"><div class="muted">لا إشعارات.</div></div>')
        for n in notifs:
            cls = _NTYPE.get(n.ntype, 'info')
            dim = '' if not n.is_read else 'opacity:.6;'
            link = Markup('<a class="btn g" href="%s">فتح</a>') % esc(n.action_url) if n.action_url else Markup('')
            mark = Markup('') if n.is_read else Markup(
                '<form method="post" action="/cafm/m/inbox/%s/read" style="margin-top:8px">%s'
                '<button class="btn g">تعليم كمقروء</button></form>') % (n.id, _csrf())
            body += Markup(
                '<div class="card" style="%s"><div class="row">'
                '<div class="h4">%s</div><span class="pill %s">%s</span></div>'
                '<div class="muted" style="margin-top:4px">%s</div>'
                '<div class="muted" style="margin-top:6px;font-size:11px">%s</div>%s%s</div>'
            ) % (Markup(dim), esc(n.title), Markup(cls),
                 esc(dict(n._fields['ntype'].selection).get(n.ntype, '')),
                 esc(n.body or ''), esc(str(n.create_date)[:16] if n.create_date else ''),
                 link, mark)
        return _shell('الإشعارات', body, accent=ACCENT)

    @http.route('/cafm/m/inbox/read-all', type='http', auth='user', methods=['POST'],
                website=False, csrf=True)
    def read_all(self, **post):
        request.env['care.cafm.notification'].sudo().search(
            [('user_id', '=', request.env.user.id), ('is_read', '=', False)]).mark_read()
        return request.redirect('/cafm/m/inbox')

    @http.route('/cafm/m/inbox/<int:nid>/read', type='http', auth='user', methods=['POST'],
                website=False, csrf=True)
    def read_one(self, nid, **post):
        n = request.env['care.cafm.notification'].sudo().browse(nid).exists()
        if n and n.user_id.id == request.env.user.id:
            n.mark_read()
        return request.redirect('/cafm/m/inbox')

    # ---------------- support tickets ----------------
    @http.route('/cafm/m/support', type='http', auth='user', website=False)
    def support(self, **kw):
        env = request.env
        if 'helpdesk.ticket' not in env:
            return _shell('الدعم', Markup(
                '<div class="card"><div class="muted">خدمة الدعم غير مفعّلة.</div></div>'),
                accent=SUPPORT_ACCENT)
        T = env['helpdesk.ticket'].sudo()
        mine = T.search([('partner_id', '=', env.user.partner_id.id)], limit=60)
        open_n = len(mine.filtered(lambda t: not t.stage_id.fold))

        body = Markup(
            '<div class="kpi"><div><div class="n">%s</div><div class="l">تذاكر مفتوحة</div></div>'
            '<div><div class="n">%s</div><div class="l">الإجمالي</div></div></div>'
        ) % (open_n, len(mine))

        teams = env['helpdesk.team'].sudo().search([], limit=20)
        topts = Markup('').join(
            Markup('<option value="%s">%s</option>') % (t.id, esc(t.name)) for t in teams)
        body += Markup(
            '<details class="card" style="margin-top:11px" open>'
            '<summary style="font-weight:900;cursor:pointer">🎧 تذكرة دعم جديدة</summary>'
            '<form method="post" action="/cafm/m/support/new" style="margin-top:10px">%s'
            '<label>الموضوع *</label><input name="name" required/>'
            '<label>القسم</label><select name="team_id">%s</select>'
            '<label>الوصف</label><textarea name="description" rows="4"></textarea>'
            '<button class="btn" style="background:%s;color:#04201c">إرسال</button></form></details>'
        ) % (_csrf(), topts, Markup(SUPPORT_ACCENT))

        if not mine:
            body += Markup('<div class="card"><div class="muted">لا تذاكر بعد.</div></div>')
        for t in mine:
            cls = 'ok' if t.stage_id.fold else 'warn'
            body += Markup(
                '<a class="card stripe" style="display:block;border-inline-start-color:%s" href="/cafm/m/support/%s">'
                '<div class="row"><div class="h4">%s</div><span class="pill %s">%s</span></div>'
                '<div class="muted" style="margin-top:4px">#%s · %s</div></a>'
            ) % (Markup(SUPPORT_ACCENT), t.id, esc(t.name), Markup(cls),
                 esc(t.stage_id.name or ''), t.id, esc(str(t.create_date)[:16] if t.create_date else ''))
        return _shell('الدعم الفني', body, accent=SUPPORT_ACCENT)

    @http.route('/cafm/m/support/new', type='http', auth='user', methods=['POST'],
                website=False, csrf=True)
    def support_new(self, **post):
        env = request.env
        name = (post.get('name') or '').strip()
        if not name or 'helpdesk.ticket' not in env:
            return request.redirect('/cafm/m/support')
        env['helpdesk.ticket'].sudo().create({
            'name': name,
            'partner_id': env.user.partner_id.id,
            'description': post.get('description') or False,
            'team_id': int(post.get('team_id') or 0) or False,
        })
        return request.redirect('/cafm/m/support')

    @http.route('/cafm/m/support/<int:tid>', type='http', auth='user', website=False)
    def support_detail(self, tid, **kw):
        env = request.env
        t = env['helpdesk.ticket'].sudo().browse(tid).exists()
        if not t or t.partner_id.id != env.user.partner_id.id:
            return request.redirect('/cafm/m/support')
        body = Markup(
            '<div class="card"><div class="row"><div class="h4">%s</div>'
            '<span class="pill %s">%s</span></div>'
            '<div class="muted" style="margin-top:6px">#%s · %s%s</div>'
            '<div style="margin-top:10px">%s</div></div>'
        ) % (esc(t.name), Markup('ok' if t.stage_id.fold else 'warn'), esc(t.stage_id.name or ''),
             t.id, esc(str(t.create_date)[:16] if t.create_date else ''),
             esc(' · %s' % t.user_id.name) if t.user_id else '',
             Markup(t.description) if t.description
             else Markup('<span class="muted">لا وصف</span>'))

        # the conversation so far
        msgs = t.message_ids.filtered(lambda m: m.message_type in ('comment', 'email'))[:30]
        if msgs:
            body += Markup('<h3 style="margin:16px 0 9px">المحادثة</h3>')
        for m in reversed(msgs):
            body += Markup(
                '<div class="card"><div class="row"><div class="h4">%s</div>'
                '<span class="muted" style="font-size:11px">%s</span></div>'
                '<div style="margin-top:6px">%s</div></div>'
            ) % (esc(m.author_id.name or ''), esc(str(m.date)[:16] if m.date else ''),
                 Markup(m.body or ''))

        body += Markup(
            '<form method="post" action="/cafm/m/support/%s/reply" class="card">%s'
            '<label>ردّك</label><textarea name="body" rows="3" required></textarea>'
            '<button class="btn" style="background:%s;color:#04201c">إرسال الرد</button></form>'
        ) % (t.id, _csrf(), Markup(SUPPORT_ACCENT))
        return _shell('تذكرة #%s' % t.id, body, accent=SUPPORT_ACCENT, back='/cafm/m/support')

    @http.route('/cafm/m/support/<int:tid>/reply', type='http', auth='user',
                methods=['POST'], website=False, csrf=True)
    def support_reply(self, tid, **post):
        env = request.env
        t = env['helpdesk.ticket'].sudo().browse(tid).exists()
        body = (post.get('body') or '').strip()
        if t and body and t.partner_id.id == env.user.partner_id.id:
            # sudo posts it, but the author stays the real person
            t.message_post(body=Markup('<p>%s</p>') % esc(body),
                           author_id=env.user.partner_id.id,
                           message_type='comment')
        return request.redirect('/cafm/m/support/%s' % tid)
