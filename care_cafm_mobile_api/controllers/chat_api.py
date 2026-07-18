# -*- coding: utf-8 -*-
"""Directory (live people search) + lightweight 1:1 chat for the app."""
from odoo import fields
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _body, API


def _person(env, u):
    emp = u.employee_id
    return {
        'uid': u.id, 'name': u.name,
        'job': (emp.job_title if emp else None) or None,
        'department': (emp.department_id.name if emp and emp.department_id else None),
        'login': u.login,
    }


class ChatApi(Controller):

    def _people_domain(self, env):
        """Users the caller may see/contact: staff who share the caller's company.
        Admins/managers see everyone. Always excludes the caller and system users."""
        u = env.user
        dom = [('id', '!=', u.id), ('share', '=', False), ('active', '=', True)]
        # keep it to real people with an employee file
        dom.append(('employee_ids', '!=', False))
        return dom

    # ---- directory: live people search ------------------------------------
    @route(API + '/directory', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def directory(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        q = (request.httprequest.args.get('q') or '').strip()
        dom = self._people_domain(env)
        if q:
            dom += ['|', '|', ('name', 'ilike', q), ('login', 'ilike', q), ('employee_ids.job_title', 'ilike', q)]
        users = env['res.users'].sudo().search(dom, order='name', limit=100)
        return _ok([_person(env, u) for u in users])

    # ---- chat threads (recent conversations) ------------------------------
    @route(API + '/chat/threads', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def chat_threads(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        uid = env.user.id
        M = env['care.chat.message'].sudo()
        msgs = M.search(['|', ('from_uid', '=', uid), ('to_uid', '=', uid)], order='id desc', limit=500)
        threads = {}
        for m in msgs:
            peer = m.to_uid if m.from_uid.id == uid else m.from_uid
            if peer.id in threads:
                t = threads[peer.id]
            else:
                t = threads[peer.id] = {'peer': _person(env, peer), 'last': None, 'last_at': None, 'unread': 0}
            if t['last'] is None:
                t['last'] = (m.body or '')[:80]
                t['last_at'] = fields.Datetime.to_string(m.create_date)
            if m.to_uid.id == uid and not m.is_read:
                t['unread'] += 1
        return _ok(list(threads.values()))

    # ---- conversation with one peer ---------------------------------------
    @route(API + '/chat/<int:peer>/messages', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def chat_messages(self, peer, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        uid = env.user.id
        M = env['care.chat.message'].sudo()
        key = M.pair_of(uid, peer)
        msgs = M.search([('pair_key', '=', key)], order='id asc', limit=500)
        # mark incoming as read
        msgs.filtered(lambda m: m.to_uid.id == uid and not m.is_read).write({'is_read': True})
        peer_u = env['res.users'].sudo().browse(peer).exists()
        return _ok({
            'peer': _person(env, peer_u) if peer_u else {'uid': peer, 'name': '—'},
            'messages': [{
                'id': m.id, 'body': m.body, 'mine': m.from_uid.id == uid,
                'at': fields.Datetime.to_string(m.create_date),
            } for m in msgs],
        })

    @route(API + '/chat/<int:peer>/send', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def chat_send(self, peer, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        body = (_body().get('body') or '').strip()
        if not body:
            return _err('الرسالة فارغة', 422)
        peer_u = env['res.users'].sudo().browse(peer).exists()
        if not peer_u:
            return _err('المستخدم غير موجود', 404)
        m = env['care.chat.message'].sudo().create({
            'from_uid': env.user.id, 'to_uid': peer, 'body': body,
        })
        # notify the recipient in the app's notification centre, if present
        if 'care.cafm.notification' in env:
            try:
                env['care.cafm.notification'].sudo().push(
                    peer_u, '💬 %s' % env.user.name, body[:120], ntype='chat')
            except Exception:
                pass
        return _ok({'id': m.id, 'at': fields.Datetime.to_string(m.create_date)})

    @route(API + '/chat/unread', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def chat_unread(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        n = env['care.chat.message'].sudo().search_count([('to_uid', '=', env.user.id), ('is_read', '=', False)])
        return _ok({'unread': n})
