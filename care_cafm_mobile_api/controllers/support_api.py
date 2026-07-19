# -*- coding: utf-8 -*-
"""In-app support desk — the app's "contact support" backed by Odoo Helpdesk:
raise a ticket, follow its status, and reply on its thread."""
from odoo import fields
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _body, _abs, _html_text, API


class SupportApi(Controller):

    def _my_domain(self, env):
        """Tickets raised by me, or belonging to my partner/company."""
        u = env.user
        p = u.partner_id
        pids = {p.id}
        if p.commercial_partner_id:
            pids.add(p.commercial_partner_id.id)
        return ['|', ('create_uid', '=', u.id), ('partner_id', 'in', list(pids))]

    def _dict(self, t, full=False):
        stage = t.stage_id
        closed = bool(getattr(stage, 'fold', False)) or (stage.name or '').lower() in (
            'solved', 'done', 'closed', 'cancelled', 'canceled')
        d = {
            'id': t.id, 'name': t.name,
            'ref': 'TKT-%05d' % t.id,
            'team': t.team_id.name or None,
            'stage': stage.name or None,
            'stage_id': stage.id or None,
            'closed': closed,
            'priority': t.priority or '0',
            'type': t.ticket_type_id.name if t.ticket_type_id else None,
            'assignee': t.user_id.name or None,
            'created': str(t.create_date)[:16] if t.create_date else None,
        }
        if full:
            msgs = []
            for m in t.message_ids.sorted('id'):
                body = _html_text(m.body or '')
                if not body:
                    continue
                msgs.append({
                    'id': m.id, 'author': m.author_id.name or None,
                    'mine': m.author_id.id == request.env.user.partner_id.id,
                    'body': body[:2000],
                    'at': str(m.date)[:16] if m.date else None,
                })
            d.update({
                'description': _html_text(t.description or '') or None,
                'email': t.partner_email or None, 'phone': t.partner_phone or None,
                'messages': msgs[-40:],
            })
        return d

    @route(API + '/support/tickets', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def tickets(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'helpdesk.ticket' not in env:
            return _ok({'available': False, 'tickets': []})
        T = env['helpdesk.ticket'].sudo()
        recs = T.search(self._my_domain(env), order='id desc', limit=100)
        rows = [self._dict(t) for t in recs]
        return _ok({
            'available': True,
            'counts': {
                'total': len(rows),
                'open': len([r for r in rows if not r['closed']]),
                'closed': len([r for r in rows if r['closed']]),
            },
            'teams': [{'id': x.id, 'name': x.name} for x in env['helpdesk.team'].sudo().search([], limit=10)],
            'tickets': rows,
        })

    @route(API + '/support/ticket/<int:tid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def ticket(self, tid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        t = env['helpdesk.ticket'].sudo().browse(tid).exists()
        if not t or t.id not in env['helpdesk.ticket'].sudo().search(self._my_domain(env)).ids:
            return _err('غير موجود', 404)
        return _ok(self._dict(t, full=True))

    @route(API + '/support/ticket/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def ticket_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'helpdesk.ticket' not in env:
            return _err('خدمة الدعم غير مفعّلة', 404)
        b = _body()
        subject = (b.get('subject') or '').strip()
        if not subject:
            return _err('اكتب موضوع الطلب', 422)
        u = env.user
        vals = {
            'name': subject,
            'description': b.get('description') or '',
            'partner_id': u.partner_id.id,
            'partner_email': u.email or u.partner_id.email or False,
            'partner_phone': u.partner_id.mobile or u.partner_id.phone or False,
            'priority': str(b.get('priority') or '1'),
        }
        if b.get('team_id'):
            vals['team_id'] = int(b['team_id'])
        else:
            team = env['helpdesk.team'].sudo().search([], limit=1)
            if team:
                vals['team_id'] = team.id
        t = env['helpdesk.ticket'].sudo().create(vals)
        # attach any photos the user added
        for i, m in enumerate(b.get('media') or []):
            data = (m.get('data') if isinstance(m, dict) else None) or ''
            if not data:
                continue
            try:
                env['ir.attachment'].sudo().create({
                    'name': (m.get('name') if isinstance(m, dict) else None) or ('media-%d' % (i + 1)),
                    'datas': data, 'res_model': 'helpdesk.ticket', 'res_id': t.id,
                    'mimetype': (m.get('mimetype') if isinstance(m, dict) else None) or 'image/jpeg'})
            except Exception:
                pass
        return _ok(self._dict(t, full=True))

    @route(API + '/support/ticket/<int:tid>/reply', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def ticket_reply(self, tid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        t = env['helpdesk.ticket'].sudo().browse(tid).exists()
        if not t or t.id not in env['helpdesk.ticket'].sudo().search(self._my_domain(env)).ids:
            return _err('غير موجود', 404)
        body = (_body().get('body') or '').strip()
        if not body:
            return _err('اكتب رسالتك', 422)
        # post with sudo (a field worker has no helpdesk write access) but keep
        # the real person as the author so the thread reads correctly.
        t.sudo().message_post(body=body, message_type='comment',
                              author_id=env.user.partner_id.id)
        return _ok(self._dict(t, full=True))
