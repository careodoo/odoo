# -*- coding: utf-8 -*-
import json
import logging
import re
from html import unescape
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

API = '/api/v1'


def _html_text(html):
    """Turn a message_post/tracking HTML body into clean plain text for the app.
    Odoo stores chatter bodies as HTML; sending them raw makes the phone show tags."""
    if not html:
        return ''
    s = str(html)
    s = re.sub(r'(?i)<br\s*/?>', '\n', s)
    s = re.sub(r'(?i)</(p|div|li|tr|h[1-6])>', '\n', s)
    s = re.sub(r'(?i)<li[^>]*>', '• ', s)
    s = re.sub(r'<[^>]+>', '', s)          # drop every remaining tag
    s = unescape(s)
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()


def _json(payload, status=200):
    return request.make_response(
        json.dumps(payload, default=str, ensure_ascii=False),
        headers=[('Content-Type', 'application/json; charset=utf-8')],
        status=status,
    )


def _ok(data=None, **extra):
    body = {'ok': True}
    if data is not None:
        body['data'] = data
    body.update(extra)
    return _json(body)


def _err(message, status=400, code=None):
    return _json({'ok': False, 'error': message, 'code': code or status}, status=status)


def _body():
    try:
        raw = request.httprequest.get_data() or b'{}'
        return json.loads(raw or b'{}')
    except Exception:
        return {}


def _bearer():
    auth = request.httprequest.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[7:].strip()
    # fallback: token query/body for easy testing
    return request.httprequest.headers.get('X-Api-Token')


def _auth():
    """Return an env bound to the token's user, or None. Record rules of that
    user apply to every query made through the returned env."""
    user = request.env['care.cafm.mobile.token'].sudo().resolve(_bearer())
    if not user:
        return None
    return request.env(user=user.id)


# ---- serializers -------------------------------------------------------------

def _service_dict(s):
    return {'id': s.id, 'name': s.name, 'type': s.service_type,
            'icon': s.icon, 'color': s.color}


def _abs(url):
    """Make a relative /web/content URL absolute for the mobile app."""
    if url and url.startswith('/'):
        return request.httprequest.host_url.rstrip('/') + url
    return url


def _wo_dict(w):
    media = []
    try:
        for m in w.media_ids[:6]:
            media.append({'url': _abs(m.url), 'thumb': _abs(m.thumbnail_url or m.url),
                          'is_video': m.media_type == 'video'})
    except Exception:
        pass
    photos = sum(1 for m in media if not m['is_video'])
    videos = sum(1 for m in media if m['is_video'])
    return {
        'id': w.id, 'name': w.name, 'title': w.title,
        'facility': w.facility_id.name, 'facility_id': w.facility_id.id,
        'location': w.location_id.name or None, 'location_id': w.location_id.id or None,
        'service': w.service_id.name, 'service_type': w.service_type,
        'employee': w.employee_id.name or None, 'employee_id': w.employee_id.id or None,
        'priority': w.priority, 'state': w.state,
        'job': w.employee_id.job_title or None,
        'request_datetime': w.request_datetime or None,
        'deadline': w.deadline or None,
        'start_datetime': w.start_datetime or None,
        'done_datetime': w.done_datetime or None,
        'duration_minutes': w.duration_minutes,
        'expected_minutes': w.expected_minutes,
        'description': w.description or None,
        'is_overdue': bool(w.is_overdue) if 'is_overdue' in w._fields else False,
        'media': media, 'photos': photos, 'videos': videos,
        'has_result': bool(w.result_description) if 'result_description' in w._fields else False,
        'result': (w.result_description or '')[:160] if 'result_description' in w._fields else '',
    }


def _can_touch_wo(env, w):
    """True if the acting user may act on this work order: its assignee,
    a supervisor/admin, or the client of its facility."""
    user = env.user
    if (user.has_group('base.group_erp_manager') or user.has_group('base.group_system')
            or user.has_group('security_management.group_security_manager')):
        return True
    if user.employee_id and w.employee_id == user.employee_id:
        return True
    if user.partner_id:
        pids = {user.partner_id.id, user.partner_id.commercial_partner_id.id}
        return w.facility_id.partner_id.id in pids
    return False


def _wo_supervisors(env, w):
    """Users who supervise this work order: its supervisor, the assignee's
    manager, else the configured shift-notify users / managers."""
    users = env['res.users'].browse()
    if w.supervisor_id:
        users |= w.supervisor_id
    if w.employee_id.parent_id.user_id:
        users |= w.employee_id.parent_id.user_id
    if not users:
        users |= env.company.sudo().cafm_shift_notify_user_ids
    if not users:
        grp = env.ref('base.group_erp_manager', raise_if_not_found=False)
        if grp:
            users |= grp.users
    return users


def _notify(env, users, title, body, ntype='task', wo=None):
    users = users.filtered(lambda u: u.active)
    if users:
        env['care.cafm.notification'].sudo().push(
            users, title, body, ntype=ntype, author=env.user,
            action_url=('/workorder/%s' % wo.id) if wo else None)


class MobileApi(http.Controller):

    # ---- auth ----------------------------------------------------------------
    @http.route(API + '/auth/login', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def login(self, **kw):
        data = _body()
        login = (data.get('login') or '').strip()
        password = data.get('password') or ''
        device = data.get('device')
        if not login or not password:
            return _err('login و password مطلوبان', 422)
        try:
            db = request.env.cr.dbname
            uid = request.env['res.users'].authenticate(db, login, password, {'interactive': False})
        except Exception:
            uid = False
        if not uid:
            return _err('بيانات الدخول غير صحيحة', 401)
        user = request.env['res.users'].sudo().browse(uid)
        tok = request.env['care.cafm.mobile.token'].sudo().issue(user, device)
        return _ok(self._me_payload(request.env(user=uid)), token=tok.token,
                   expiry=str(tok.expiry))

    @http.route(API + '/auth/signup', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def signup(self, **kw):
        """Public self-registration → a CARE 2 CARE customer (portal user).
        Extra permissions (CAFM/PMS/…) are granted by an admin later."""
        b = _body()
        name = (b.get('name') or '').strip()
        email = (b.get('email') or '').strip().lower()
        phone = (b.get('phone') or '').strip()
        pw = b.get('password') or ''
        if not name or not (email or phone):
            return _err('الاسم والبريد أو الهاتف مطلوبان', 422)
        if len(pw) < 6:
            return _err('كلمة المرور 6 أحرف على الأقل', 422)
        login = email or phone
        Users = request.env['res.users'].sudo()
        if Users.with_context(active_test=False).search_count([('login', '=', login)]):
            return _err('يوجد حساب بهذا البريد/الهاتف بالفعل', 409)
        try:
            portal = request.env.ref('base.group_portal')
            user = Users.with_context(no_reset_password=True, mail_create_nosubscribe=True).create({
                'name': name, 'login': login,
                'email': email or False, 'phone': phone or False,
                'password': pw, 'groups_id': [(6, 0, [portal.id])],
            })
        except Exception as e:
            return _err('تعذّر إنشاء الحساب: %s' % e, 422)
        tok = request.env['care.cafm.mobile.token'].sudo().issue(user, b.get('device'))
        return _ok(self._me_payload(request.env(user=user.id)), token=tok.token, expiry=str(tok.expiry))

    @http.route(API + '/auth/logout', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def logout(self, **kw):
        rec = request.env['care.cafm.mobile.token'].sudo().search(
            [('token', '=', _bearer())], limit=1)
        rec.write({'active': False}) if rec else None
        return _ok({'loggedOut': True})

    # ---- profile / bootstrap -------------------------------------------------
    def _me_payload(self, env):
        user = env.user
        emp = user.employee_id
        WO = env['care.cafm.workorder']
        my = WO.search([('employee_id', '=', emp.id)]) if emp else WO.browse()
        # service types the user actually works on → drives which service app opens
        my_types = sorted(set(t for t in my.mapped('service_type') if t)) if my else []
        # sudo: portal/client users can't read the service catalogue directly
        services = env['care.cafm.service'].sudo().search([])
        is_supervisor = bool(user.has_group('base.group_erp_manager')
                             or user.has_group('security_management.group_security_manager'))
        is_admin = bool(user.has_group('base.group_system'))
        # may this user add workers? supervisor/admin always; a client only when
        # their company partner is flagged (cafm_can_add_workers).
        _cp = user.partner_id.commercial_partner_id or user.partner_id
        can_add_workers = bool(is_supervisor or is_admin
                               or (_cp and _cp.sudo().cafm_can_add_workers))
        # role hint drives the app's default face: a security guard opens the
        # security app, a cleaner the cleaning app, etc.
        is_cafm_member = ('care.cafm.client' in env
                          and bool(env['care.cafm.client'].sudo().search_count([('user_ids', 'in', [user.id])])))
        if not emp or is_cafm_member:
            role = 'client'
        elif 'security' in my_types:
            role = 'security'
        elif my_types:
            role = my_types[0]  # cleaning / agriculture / facade / ...
        else:
            role = 'worker'
        return {
            'user': {'id': user.id, 'name': user.name, 'login': user.login,
                     'employee_id': emp.id or None, 'email': user.email or None},
            'role': role,
            'is_supervisor': is_supervisor,
            'is_admin': is_admin,
            'can_add_workers': can_add_workers,
            'my_service_types': my_types,
            'services': [_service_dict(s) for s in services],
            'counts': self._my_counts(env, emp),
            'unread_notifications': env['care.cafm.notification'].search_count(
                [('user_id', '=', user.id), ('is_read', '=', False)]),
        }

    def _my_counts(self, env, emp):
        WO = env['care.cafm.workorder']
        if not emp:
            return {'open': 0, 'in_progress': 0, 'done': 0, 'overdue': 0, 'total': 0}
        mine = WO.search([('employee_id', '=', emp.id)])
        return {
            'total': len(mine),
            'open': len(mine.filtered(lambda w: w.state not in ('done', 'verified', 'cancelled'))),
            'in_progress': len(mine.filtered(lambda w: w.state == 'in_progress')),
            'done': len(mine.filtered(lambda w: w.state in ('done', 'verified'))),
            'overdue': len(mine.filtered('is_overdue')),
            # kept for backward-compat with the first app build
            'open_workorders': len(mine.filtered(lambda w: w.state not in ('done', 'verified', 'cancelled'))),
        }

    @http.route(API + '/me', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def me(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        return _ok(self._me_payload(env))

    @http.route(API + '/services', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def services(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        return _ok([_service_dict(s) for s in env['care.cafm.service'].sudo().search([('active', '=', True)])])

    # ---- work orders ---------------------------------------------------------
    @http.route(API + '/workorders', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def workorders(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        emp = env.user.employee_id
        dom = [('employee_id', '=', emp.id)] if emp else [('id', '=', 0)]
        state = request.httprequest.args.get('state')
        if state == 'open':
            dom.append(('state', 'not in', ('done', 'verified', 'cancelled')))
        wos = env['care.cafm.workorder'].search(dom, limit=200)
        return _ok([_wo_dict(w) for w in wos])

    @http.route(API + '/workorders/<int:wid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def workorder_get(self, wid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        w = env['care.cafm.workorder'].browse(wid).exists()
        if not w:
            return _err('غير موجود', 404)
        return _ok(_wo_dict(w))

    @http.route(API + '/workorders/<int:wid>/detail', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def workorder_detail(self, wid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        # Read with sudo (history/media/other-users' WOs are ACL-restricted), but
        # gate access: own WO / supervisor / admin / the client of its facility.
        w = env['care.cafm.workorder'].sudo().browse(wid).exists()
        if not w:
            return _err('غير موجود', 404)
        user = env.user
        allowed = bool(user.has_group('base.group_erp_manager') or user.has_group('base.group_system')
                       or user.has_group('security_management.group_security_manager')
                       or (user.employee_id and w.employee_id == user.employee_id))
        if not allowed and user.partner_id:
            pids = {user.partner_id.id, user.partner_id.commercial_partner_id.id}
            allowed = w.facility_id.partner_id.id in pids
        if not allowed:
            return _err('لا صلاحية لعرض هذه المهمة', 403)
        d = _wo_dict(w)
        loc = w.location_id
        loc_detail = None
        if loc:
            loc_detail = {
                'facility': w.facility_id.name or None,
                'building': loc.building_id.name or None,
                'floor': loc.floor_id.name or None,
                'name': loc.name or None,
                'code': loc.code or None,
                'type': loc.location_type,
                # a ready-to-show one-line path: المرفق ← المبنى ← الدور ← الموقع (الرمز)
                'full': ' ← '.join(filter(None, [
                    w.facility_id.name, loc.building_id.name, loc.floor_id.name,
                    '%s%s' % (loc.name or '', ' (%s)' % loc.code if loc.code else ''),
                ])),
            }
        is_supervisor = bool(user.has_group('base.group_erp_manager') or user.has_group('base.group_system')
                             or user.has_group('security_management.group_security_manager'))
        _cp = user.partner_id.commercial_partner_id or user.partner_id
        is_client_mgr = bool(_cp and _cp.sudo().cafm_can_add_workers)
        can_review = is_supervisor or is_client_mgr
        is_assignee = bool(user.employee_id and w.employee_id == user.employee_id)
        missing = w.proof_missing()
        media = [{'id': m.id, 'name': m.name, 'type': m.media_type,
                  'is_video': m.media_type == 'video',
                  'url': _abs(m.url), 'thumb': _abs(m.thumbnail_url or m.url)} for m in w.media_ids]
        d.update({
            'assignee': w.employee_id.name or None,
            'location_detail': loc_detail,
            'map_query': ' '.join(filter(None, [loc.name if loc else None, w.facility_id.name, w.facility_id.address or ''])),
            'instructions': w.instructions or None,
            'media': media,
            # ---- proof requirements + live status ----
            'proof': {'presence': w.proof_presence, 'photo': w.proof_photo, 'video': w.proof_video},
            'presence_verified': w.presence_verified,
            'proof_missing': missing,
            'rejection_count': w.rejection_count,
            # ---- النتيجة (result the worker submits) ----
            'result': {
                'description': w.result_description or None,
                'photos': [m for m in media if not m['is_video'] and m['type'] != 'document'],
                'videos': [m for m in media if m['is_video']],
                'submitted': w.state in ('done', 'verified'),
            },
            # ---- action gating for the UI ----
            'can_submit': bool(is_assignee and w.state in ('assigned', 'in_progress') and not missing),
            'can_approve': bool(can_review and w.state == 'done'),
            'can_reject': bool(can_review and w.state == 'done'),
            'client_rating': int(w.client_rating) if ('client_rating' in w._fields and w.client_rating) else 0,
            'client_feedback': (w.client_feedback if 'client_feedback' in w._fields else None) or None,
            'can_rate': bool(is_client_mgr and w.state in ('done', 'verified')),
            'history': [{
                'author': msg.author_id.name or 'النظام',
                'body': _html_text(msg.body),
                'date': msg.date,
            } for msg in w.message_ids.sorted('date', reverse=True)[:20]
                if (msg.message_type != 'notification' or msg.body) and _html_text(msg.body)],
        })
        return _ok(d)

    @http.route(API + '/workorders/<int:wid>/verify', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def workorder_verify(self, wid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        _cp = env.user.partner_id.commercial_partner_id or env.user.partner_id
        if not (env.user.has_group('base.group_erp_manager')
                or env.user.has_group('base.group_system')
                or env.user.has_group('security_management.group_security_manager')
                or (_cp and _cp.sudo().cafm_can_add_workers)):
            return _err('الاعتماد للمشرفين أو العميل المخوّل', 403)
        w = env['care.cafm.workorder'].sudo().browse(wid).exists()
        if not w:
            return _err('غير موجود', 404)
        try:
            w.action_verify()
        except Exception as e:
            return _err(str(e), 400)
        if w.employee_id.user_id:
            _notify(env, w.employee_id.user_id, 'تم اعتماد مهمتك',
                    'اعتُمدت نتيجة: %s' % w.title, ntype='info', wo=w)
        return _ok(_wo_dict(w))

    @http.route(API + '/workorders/<int:wid>/note', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def workorder_note(self, wid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        # sudo: field workers/clients can't message_post on a WO they don't own via ACL.
        w = env['care.cafm.workorder'].sudo().browse(wid).exists()
        if not w:
            return _err('غير موجود', 404)
        if not _can_touch_wo(env, w):
            return _err('لا صلاحية على هذه المهمة', 403)
        body = (_body().get('note') or '').strip()
        if body:
            author = env.user.partner_id.id
            email = env.user.email or env.company.email or 'noreply@ecare.care-kw.com'
            try:
                w.message_post(body=body, email_from=email, author_id=author)
            except Exception as e:
                _logger.exception('workorder note failed')
                return _err(str(e), 400)
        return _ok({'ok': True})

    @http.route(API + '/workorders/<int:wid>/photo', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def workorder_photo(self, wid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        w = env['care.cafm.workorder'].sudo().browse(wid).exists()
        if not w:
            return _err('غير موجود', 404)
        b = _body()
        data = b.get('data')  # base64 (no data: prefix)
        if not data:
            return _err('data (base64) مطلوب', 422)
        filename = b.get('filename') or 'photo.jpg'
        mtype = b.get('media_type') or 'photo'  # photo | video
        try:
            m = env['care.cafm.media'].sudo().store_binary(
                data, filename, res_model='care.cafm.workorder', res_id=w.id, media_type=mtype)
        except Exception as e:
            return _err(str(e), 400)
        w.sudo()._cafm_log('📎 أُرفقت %s للاعتماد.' % ('صورة' if mtype == 'photo' else 'فيديو'))
        return _ok({'id': m.id, 'url': _abs(m.url), 'type': m.media_type})

    @http.route(API + '/workorders/<int:wid>/start', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def workorder_start(self, wid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        # sudo: field workers lack write on the WO / create on care.cafm.scan.
        w = env['care.cafm.workorder'].sudo().browse(wid).exists()
        if not w:
            return _err('غير موجود', 404)
        if not _can_touch_wo(env, w):
            return _err('لا صلاحية على هذه المهمة', 403)
        try:
            w.action_scan_start()
        except Exception as e:
            _logger.exception('workorder start failed')
            return _err(str(e), 400)
        return _ok(_wo_dict(w))

    @http.route(API + '/workorders/<int:wid>/done', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def workorder_done(self, wid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        w = env['care.cafm.workorder'].sudo().browse(wid).exists()
        if not w:
            return _err('غير موجود', 404)
        if not _can_touch_wo(env, w):
            return _err('لا صلاحية على هذه المهمة', 403)
        desc = (_body().get('result_description') or '').strip()
        if desc:
            w.result_description = desc
        try:
            w.action_done()
        except Exception as e:
            _logger.exception('workorder done failed')
            return _err(str(e), 400)
        # notify the supervisor(s) that the result awaits approval
        _notify(env, _wo_supervisors(env, w), 'نتيجة بانتظار الاعتماد',
                '%s أكمل: %s' % (w.employee_id.name or '', w.title), wo=w)
        return _ok(_wo_dict(w))

    @http.route(API + '/workorders/<int:wid>/reject', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def workorder_reject(self, wid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        _cp = env.user.partner_id.commercial_partner_id or env.user.partner_id
        if not (env.user.has_group('base.group_erp_manager')
                or env.user.has_group('base.group_system')
                or env.user.has_group('security_management.group_security_manager')
                or (_cp and _cp.sudo().cafm_can_add_workers)):
            return _err('الإرجاع للمشرفين أو العميل المخوّل', 403)
        w = env['care.cafm.workorder'].sudo().browse(wid).exists()
        if not w:
            return _err('غير موجود', 404)
        reason = (_body().get('reason') or '').strip()
        try:
            w.action_reject(reason=reason or None)
        except Exception as e:
            _logger.exception('workorder reject failed')
            return _err(str(e), 400)
        if w.employee_id.user_id:
            _notify(env, w.employee_id.user_id, 'أُرجعت المهمة',
                    'يجب إعادة تنفيذ: %s%s' % (w.title, (' — ' + reason) if reason else ''),
                    ntype='warning', wo=w)
        return _ok(_wo_dict(w))

    @http.route(API + '/workorders/<int:wid>/rate', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def workorder_rate(self, wid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        _cp = env.user.partner_id.commercial_partner_id or env.user.partner_id
        if not (_cp and _cp.sudo().cafm_can_add_workers) and not (
                env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system')):
            return _err('التقييم للعميل المخوّل', 403)
        w = env['care.cafm.workorder'].sudo().browse(wid).exists()
        if not w:
            return _err('غير موجود', 404)
        b = _body()
        rating = str(b.get('rating') or '').strip()
        if rating not in ('1', '2', '3', '4', '5'):
            return _err('تقييم غير صالح (1–5)', 422)
        w.write({'client_rating': rating, 'client_feedback': (b.get('feedback') or '').strip() or False,
                 'client_rated_date': fields.Datetime.now()})
        try:
            w.message_post(body='⭐ قيّم العميل التنفيذ: %s/5%s' % (
                rating, ((' — ' + b.get('feedback')) if b.get('feedback') else '')))
            if w.employee_id.user_id:
                _notify(env, w.employee_id.user_id, 'تقييم جديد',
                        'قيّم العميل مهمتك «%s» بـ %s/5' % (w.title, rating), ntype='info', wo=w)
        except Exception:
            pass
        return _ok({'id': w.id, 'client_rating': int(rating)})

    # ---- QR scan -------------------------------------------------------------
    @http.route(API + '/scan', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def scan(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        code = (_body().get('code') or '').strip()
        if not code:
            return _err('code مطلوب', 422)
        loc = env['care.cafm.location'].search([('code', '=', code)], limit=1)
        if not loc:
            return _err('رمز غير معروف', 404)
        emp = env.user.employee_id
        # log a presence scan
        if emp:
            env['care.cafm.scan'].sudo().create({
                'employee_id': emp.id, 'location_id': loc.id, 'scan_type': 'start_task'})
        wos = env['care.cafm.workorder'].search([
            ('location_id', '=', loc.id),
            ('state', 'not in', ('done', 'verified', 'cancelled'))], limit=50)
        return _ok({
            'location': {'id': loc.id, 'name': loc.name, 'code': loc.code,
                         'facility': loc.facility_id.name,
                         'is_checkpoint': loc.is_checkpoint,
                         'type': loc.location_type},
            'workorders': [_wo_dict(w) for w in wos],
        })
