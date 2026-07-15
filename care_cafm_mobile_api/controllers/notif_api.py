# -*- coding: utf-8 -*-
"""Notification inbox for the app: list, unread count, mark read."""
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _body, API


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

    # ---- device push registration (FCM) -----------------------------------
    @route(API + '/notifications/register', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def register_device(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        b = _body()
        token = b.get('token')
        if not token:
            return _err('رمز الجهاز مطلوب', 422)
        dev = env['care.cafm.device'].sudo().register(
            env.user, token, platform=b.get('platform', 'android'), device_name=b.get('device_name'))
        return _ok({'id': dev.id, 'registered': True})

    @route(API + '/notifications/unregister', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def unregister_device(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        token = _body().get('token')
        if token:
            env['care.cafm.device'].sudo().search(
                [('token', '=', token), ('user_id', '=', env.user.id)]).write({'active': False})
        return _ok({'unregistered': True})

    @route(API + '/notifications/test', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def test_push(self, **kw):
        """Send a test push to the caller's own devices — for verifying setup."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        env['care.cafm.notification'].push(
            env.user, '🔔 اختبار الإشعارات', 'وصلك هذا الإشعار بنجاح من CARE.', ntype='info')
        return _ok({'sent': True})

    # ---- account & data deletion (Google Play requirement) ----------------
    @route(API + '/account/info', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def account_info(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        u = env.user
        p = u.partner_id
        # account type
        atype = 'عميل' if u.has_group('base.group_portal') else ('مدير' if u.has_group('base.group_system') else 'مستخدم داخلي')
        clients = env['care.cafm.client'].sudo().search([('user_ids', 'in', [u.id])]) if 'care.cafm.client' in env else None
        stats = {}
        if clients:
            stats['company'] = clients[:1].partner_id.name
            stats['projects'] = len(clients.mapped('project_ids')) if 'project_ids' in clients._fields else 0
        return _ok({
            'name': u.name, 'login': u.login, 'email': u.email or None,
            'phone': p.phone or p.mobile or None, 'company': stats.get('company') or (p.commercial_partner_id.name if p.commercial_partner_id != p else None),
            'account_type': atype, 'projects': stats.get('projects', 0),
            'unread': env['care.cafm.notification'].search_count([('user_id', '=', u.id), ('is_read', '=', False)]),
        })

    @route(API + '/account/change_password', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def account_change_password(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        b = _body()
        old, new = b.get('old'), b.get('new')
        if not new or len(new) < 6:
            return _err('كلمة المرور الجديدة قصيرة (6 أحرف على الأقل)', 422)
        try:
            env['res.users'].sudo().authenticate(env.cr.dbname, env.user.login, old, {'interactive': False})
        except Exception:
            return _err('كلمة المرور الحالية غير صحيحة', 403)
        env.user.sudo().write({'password': new})
        return _ok({'changed': True})

    @route(API + '/account/delete_request', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def account_delete_request(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        reason = _body().get('reason')
        rec = env['care.account.deletion'].sudo().submit(env.user, reason)
        return _ok({'requested': True, 'id': rec.id, 'state': rec.state})
