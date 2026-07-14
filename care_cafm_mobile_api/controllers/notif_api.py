# -*- coding: utf-8 -*-
"""Notification inbox for the app: list, unread count, mark read."""
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, API


def _notif_dict(n):
    return {
        'id': n.id, 'title': n.title, 'body': n.body or None,
        'type': n.ntype, 'is_read': n.is_read,
        'author': n.author_id.name or None,
        'action_url': n.action_url or None,
        'date': n.create_date,
    }


class NotifApi(Controller):

    @route(API + '/notifications', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def notifications(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        recs = env['care.cafm.notification'].search(
            [('user_id', '=', env.user.id)], limit=100)
        unread = env['care.cafm.notification'].search_count(
            [('user_id', '=', env.user.id), ('is_read', '=', False)])
        return _ok([_notif_dict(n) for n in recs], unread=unread)

    @route(API + '/notifications/<int:nid>/read', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def read_one(self, nid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        n = env['care.cafm.notification'].search([('id', '=', nid), ('user_id', '=', env.user.id)])
        if not n:
            return _err('غير موجود', 404)
        n.mark_read()
        return _ok({'id': nid, 'is_read': True})

    @route(API + '/notifications/read_all', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def read_all(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        env['care.cafm.notification'].search(
            [('user_id', '=', env.user.id), ('is_read', '=', False)]).mark_read()
        return _ok({'ok': True})
