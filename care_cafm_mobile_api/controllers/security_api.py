# -*- coding: utf-8 -*-
"""Security-service endpoints for the mobile app. These read/write the real
*Security Manager* (security.* models) — the same module that runs standalone.
Reads use sudo() because security.* models are ACL-restricted to security groups,
while the field app must work for any authenticated guard device."""
from odoo import fields
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _body, API


def _incident_dict(i):
    return {
        'id': i.id, 'name': i.name,
        'type': i.incident_type, 'severity': i.severity,
        'state': i.state, 'date': i.date or None,
        'premise': i.premise_id.name or None,
        'description': i.description or None,
    }


def _patrol_dict(p):
    return {
        'id': p.id, 'name': p.name,
        'guard': p.guard_id.name or None,
        'route': p.route_id.name or None,
        'premise': p.premise_id.name or None,
        'state': p.state,
        'start_time': p.start_time or None,
        'end_time': p.end_time or None,
        'points': len(p.patrol_point_ids),
    }


def _gatepass_dict(g):
    return {'id': g.id, 'name': g.name, 'visitor': g.visitor_name,
            'state': g.state, 'premise': g.premise_id.name or None,
            'purpose': g.purpose or None}


def _key_dict(k):
    return {'id': k.id, 'name': k.name, 'state': k.state,
            'premise': k.premise_id.name or None,
            'holder': k.current_holder_id.name or None}


def _n(rec):
    return rec.name if rec else None


# kind -> (model, order, serializer) — mirrors the main Security Manager sections
SECTIONS = {
    'guards': ('security.guard', 'name', lambda g: {
        'id': g.id, 'title': g.name, 'sub': (g.phone or '') + (' · ' + g.post_site if g.post_site else ''),
        'status': 'متصل' if g.last_check_in else 'غير متصل',
        'meta': _n(g.last_location_id)}),
    'teams': ('security.team', 'name', lambda t: {
        'id': t.id, 'title': t.name, 'sub': 'قائد: ' + (_n(t.leader_id) or '—') + ' · ' + (_n(t.client_id) or '—'),
        'status': str(t.member_count) + ' أعضاء', 'meta': 'مهام %s · دوريات %s' % (t.task_count, t.patrol_count)}),
    'schedules': ('security.shift.assignment', 'date desc', lambda s: {
        'id': s.id, 'title': s.name or _n(s.security_employee_id), 'sub': _n(s.security_employee_id),
        'status': s.state, 'meta': str(s.date or '')}),
    'patrol_points': ('security.patrol.point', 'name', lambda p: {
        'id': p.id, 'title': p.name, 'sub': (p.code or '') + ' · ' + (_n(p.premise_id) or ''),
        'status': p.point_type, 'meta': 'التالي: ' + str(p.next_check_time or '—')}),
    'patrol_logs': ('security.patrol.log', 'timestamp desc', lambda l: {
        'id': l.id, 'title': l.name or 'سجل', 'sub': _n(l.guard_id) or _n(l.security_employee_id),
        'status': 'مشكلة' if l.issue_detected else 'سليم', 'meta': str(l.timestamp or '')}),
    'inspections': ('security.inspection', 'scheduled_date desc', lambda i: {
        'id': i.id, 'title': i.name, 'sub': 'مفتّش: ' + (_n(i.inspector_id) or '—'),
        'status': i.severity or i.inspection_type, 'meta': str(i.scheduled_date or '')}),
    'tasks': ('security.task', 'deadline', lambda t: {
        'id': t.id, 'title': t.name, 'sub': 'إلى: ' + (_n(t.assigned_to) or _n(t.assigned_team_id) or '—'),
        'status': t.priority, 'meta': 'إنجاز %s%% · %s' % (int(t.progress or 0), t.deadline or '')}),
}


def _row(label, value):
    if value in (None, False, ''):
        return None
    if hasattr(value, 'name'):   # a recordset → its display name
        value = value.name
    return {'label': label, 'value': str(value)}


# kind -> (model, list of (label, field-getter)) for the tap-to-open detail view
DETAILS = {
    'guards': ('security.guard', lambda g: [
        _row('الاسم', g.name), _row('الهاتف', g.phone), _row('الموقع', g.post_site),
        _row('آخر موقع', _n(g.last_location_id)), _row('آخر تسجيل', g.last_check_in),
        _row('الحالة', 'متصل' if g.last_check_in else 'غير متصل')]),
    'teams': ('security.team', lambda t: [
        _row('الفريق', t.name), _row('القائد', _n(t.leader_id)), _row('العميل', _n(t.client_id)),
        _row('عدد الأعضاء', t.member_count), _row('المهام', t.task_count), _row('الدوريات', t.patrol_count)]),
    'schedules': ('security.shift.assignment', lambda s: [
        _row('المرجع', s.name), _row('الموظف', _n(s.security_employee_id)),
        _row('التاريخ', s.date), _row('الحالة', s.state)]),
    'patrol_points': ('security.patrol.point', lambda p: [
        _row('النقطة', p.name), _row('الرمز', p.code), _row('الموقع', _n(p.premise_id)),
        _row('النوع', p.point_type), _row('الفحص التالي', p.next_check_time)]),
    'patrol_logs': ('security.patrol.log', lambda l: [
        _row('السجل', l.name), _row('الحارس', _n(l.guard_id) or _n(l.security_employee_id)),
        _row('الوقت', l.timestamp), _row('مشكلة؟', 'نعم' if l.issue_detected else 'لا'),
        _row('ملاحظات', getattr(l, 'notes', None))]),
    'inspections': ('security.inspection', lambda i: [
        _row('التفتيش', i.name), _row('المفتّش', _n(i.inspector_id)), _row('النوع', i.inspection_type),
        _row('الخطورة', i.severity), _row('الموعد', i.scheduled_date),
        _row('الملاحظات', getattr(i, 'notes', None) or getattr(i, 'description', None))]),
    'tasks': ('security.task', lambda t: [
        _row('المهمة', t.name), _row('المكلّف', _n(t.assigned_to) or _n(t.assigned_team_id)),
        _row('الأولوية', t.priority), _row('الإنجاز', '%s%%' % int(t.progress or 0)),
        _row('الموعد', t.deadline), _row('الوصف', getattr(t, 'description', None))]),
}


class SecurityMobileApi(Controller):

    @route(API + '/security/record/<string:kind>/<int:rid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def sec_record(self, kind, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        cfg = DETAILS.get(kind)
        if not cfg:
            return _err('قسم غير معروف', 404)
        model, ser = cfg
        rec = env[model].sudo().browse(rid).exists()
        if not rec:
            return _err('غير موجود', 404)
        rows = [r for r in ser(rec) if r]
        return _ok({'id': rec.id, 'title': rec.display_name, 'rows': rows})

    @route(API + '/security/data/<string:kind>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def sec_data(self, kind, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        cfg = SECTIONS.get(kind)
        if not cfg:
            return _err('قسم غير معروف', 404)
        model, order, ser = cfg
        recs = env[model].sudo().search([], order=order, limit=100)
        return _ok([ser(r) for r in recs])

    @route(API + '/security/dashboard', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def sec_dashboard(self, kind=None, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        def c(m, dom=None):
            return env[m].sudo().search_count(dom or []) if m in env else 0
        return _ok({
            'guards': c('security.guard'),
            'teams': c('security.team'),
            'patrols_active': c('security.patrol', [('state', '=', 'in_progress')]),
            'incidents_open': c('security.incident.report', [('state', 'not in', ('closed', 'resolved'))]),
            'gatepasses_valid': c('security.gate.pass', [('state', '=', 'valid')]),
            'keys_out': c('security.key', [('state', '=', 'checked_out')]),
            'inspections': c('security.inspection'),
            'tasks_open': c('security.task', [('progress', '<', 100)]),
        })


    @route(API + '/security/incidents', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def incidents(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        recs = env['security.incident.report'].sudo().search([], order='date desc', limit=50)
        return _ok([_incident_dict(i) for i in recs])

    @route(API + '/security/incidents', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def incident_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        b = _body()
        Premise = env['security.premise'].sudo()
        premise = Premise.browse(int(b['premise_id'])) if b.get('premise_id') else Premise.search([], limit=1)
        if not premise:
            return _err('لا يوجد موقع أمني مُعرّف', 422)
        desc = (b.get('description') or '').strip()
        if not desc:
            return _err('description مطلوب', 422)
        vals = {
            'date': fields.Datetime.now(),
            'premise_id': premise.id,
            'incident_type': b.get('type') or 'other',
            'severity': b.get('severity') or 'medium',
            'description': desc,
            'reporter_id': env.user.id,
        }
        Incident = env['security.incident.report'].sudo()
        # Let the model's sequence assign the reference (IR/YYYY/NNNN); only set
        # name ourselves if the model genuinely requires one with no default.
        if Incident._fields.get('name') and Incident._fields['name'].required \
                and not Incident.default_get(['name']).get('name'):
            vals['name'] = (b.get('title') or desc)[:60]
        rec = Incident.create(vals)
        return _ok(_incident_dict(rec))

    @route(API + '/security/patrols', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def patrols(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        recs = env['security.patrol'].sudo().search([], order='start_time desc', limit=50)
        return _ok([_patrol_dict(p) for p in recs])

    @route(API + '/security/gatepasses', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def gatepasses(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        recs = env['security.gate.pass'].sudo().search([], order='create_date desc', limit=50)
        return _ok([_gatepass_dict(g) for g in recs])

    @route(API + '/security/keys', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def keys(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        recs = env['security.key'].sudo().search([], order='name', limit=100)
        return _ok([_key_dict(k) for k in recs])


class SecurityIncidentExtra(Controller):
    """Evidence, updates, location and escalation for an incident — the things
    that cannot be reconstructed an hour later."""

    @route(API + '/security/incident/<int:iid>', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def incident_detail(self, iid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        i = env['security.incident.report'].sudo().browse(iid).exists()
        if not i:
            return _err('غير موجود', 404)
        base = env['ir.config_parameter'].sudo().get_param('web.base.url', '').rstrip('/')
        return _ok({
            'id': i.id, 'name': i.name,
            'type': i.incident_type, 'severity': i.severity,
            'location': i.location or None,
            'located': i.located, 'map_url': i.map_url or None,
            'lat': i.latitude, 'lng': i.longitude,
            'description': i.description or None,
            'state': i.state,
            'live_active': i.live_active, 'live_url': i.live_url or None,
            'workorder': i.workorder_id.display_name or None,
            'media': [{
                'id': m.id, 'kind': m.kind, 'caption': m.name or None,
                'url': '%s/web/image/security.incident.media/%s/file' % (base, m.id),
                'at': str(m.taken_at or '')[:16],
            } for m in i.media_ids],
            'updates': [{
                'id': u.id, 'body': u.body, 'by': u.user_id.name or None,
                'at': str(u.at or '')[:16],
            } for u in i.update_ids],
        })

    @route(API + '/security/incident/<int:iid>/media', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def incident_media(self, iid, **kw):
        """Attach a photo or clip taken at the scene."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        i = env['security.incident.report'].sudo().browse(iid).exists()
        if not i:
            return _err('غير موجود', 404)
        b = _body()
        if not b.get('file'):
            return _err('لا ملف', 422)
        m = env['security.incident.media'].sudo().create({
            'incident_id': i.id, 'kind': b.get('kind') or 'photo',
            'name': b.get('caption') or False, 'file': b['file'],
            'filename': b.get('filename') or 'evidence',
        })
        return _ok({'id': m.id, 'count': len(i.media_ids)})

    @route(API + '/security/incident/<int:iid>/update', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def incident_update(self, iid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        i = env['security.incident.report'].sudo().browse(iid).exists()
        if not i:
            return _err('غير موجود', 404)
        b = _body()
        if not (b.get('body') or '').strip():
            return _err('النص مطلوب', 422)
        i.action_add_update(b['body'], user_id=env.user.id)
        return _ok({'count': len(i.update_ids)})

    @route(API + '/security/incident/<int:iid>/locate', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def incident_locate(self, iid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        i = env['security.incident.report'].sudo().browse(iid).exists()
        if not i:
            return _err('غير موجود', 404)
        b = _body()
        i.write({'latitude': float(b.get('lat') or 0),
                 'longitude': float(b.get('lng') or 0)})
        return _ok({'located': i.located, 'map_url': i.map_url or None})

    @route(API + '/security/incident/<int:iid>/live', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def incident_live(self, iid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        i = env['security.incident.report'].sudo().browse(iid).exists()
        if not i:
            return _err('غير موجود', 404)
        b = _body()
        i.write({'live_active': bool(b.get('active')),
                 'live_url': b.get('url') or i.live_url})
        return _ok({'live_active': i.live_active, 'live_url': i.live_url or None})

    @route(API + '/security/incident/<int:iid>/to_workorder', type='http',
           auth='public', methods=['POST'], csrf=False, cors='*')
    def incident_to_workorder(self, iid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        i = env['security.incident.report'].sudo().browse(iid).exists()
        if not i:
            return _err('غير موجود', 404)
        try:
            wo = i.action_to_workorder()
        except Exception as e:
            return _err(str(e) or 'تعذّر', 422)
        return _ok({'workorder': wo.display_name, 'workorder_id': wo.id})
