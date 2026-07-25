# -*- coding: utf-8 -*-
"""Security-service endpoints for the mobile app. These read/write the real
*Security Manager* (security.* models) — the same module that runs standalone.
Reads use sudo() because security.* models are ACL-restricted to security groups,
while the field app must work for any authenticated guard device."""
from odoo import fields
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _body, API


def _incident_dict(i):
    def _lbl(f, v):
        try:
            return dict(i._fields[f].selection).get(v, v)
        except Exception:
            return v
    return {
        'id': i.id, 'name': i.name,
        'type': i.incident_type, 'type_label': _lbl('incident_type', i.incident_type),
        'severity': i.severity, 'severity_label': _lbl('severity', i.severity),
        'state': i.state, 'state_label': _lbl('state', i.state),
        'date': str(i.date or '')[:16] or None,
        'premise': i.premise_id.name or None,
        'location': i.location or None,
        'description': i.description or None,
        'media_count': len(i.media_ids) if 'media_ids' in i._fields else 0,
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


    @route(API + '/security/my_team', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def my_team(self, **kw):
        """The teams the current guard belongs to + their fellow members (photo,
        role, presence, post) — the «My Team» screen. Guards see only their own
        teams, not the whole roster."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'security.team' not in env or 'security.employee' not in env:
            return _ok({'teams': [], 'me': None})
        SE = env['security.employee'].sudo()
        me = SE.search([('employee_id.user_id', '=', env.uid)], limit=1)
        Team = env['security.team'].sudo()
        teams = Team.search(['|', ('member_ids', 'in', me.ids), ('leader_id', 'in', me.ids)]) if me else Team.browse()

        def _member(se, leader_id):
            hr = se.employee_id
            img = None
            try:
                img = (se.image_1920 or (hr.image_256 if hr else None))
                img = img.decode() if img else None
            except Exception:
                img = None
            return {
                'id': se.id, 'name': se.name,
                'is_me': se.id == me.id if me else False,
                'is_leader': se.id == leader_id,
                'role': se.role_id.name if se.role_id else None,
                'badge': se.badge_number or None,
                'phone': se.phone or None,
                'available': bool(se.is_available),
                'photo_b64': img,
                'user_id': hr.user_id.id if (hr and hr.user_id) else None,
                'shift': se.current_shift_id.display_name if se.current_shift_id else None,
            }
        out = []
        for t in teams:
            members = list(t.member_ids)
            if t.leader_id and t.leader_id not in members:
                members = [t.leader_id] + members
            out.append({
                'id': t.id, 'name': t.name,
                'client': t.client_id.name if t.client_id else None,
                'premise': t.premise_id.name if t.premise_id else None,
                'shift_type': t.shift_type_id.name if t.shift_type_id else None,
                'member_count': len(members),
                'members': [_member(m, t.leader_id.id if t.leader_id else 0) for m in members],
            })
        return _ok({
            'teams': out,
            'me': {'id': me.id, 'name': me.name} if me else None,
        })

    # ==== Key custody =====================================================
    def _key_full(self, k, with_log=False):
        holder = k.current_holder_id
        d = {
            'id': k.id, 'name': k.name,
            'door_number': k.door_number or None,
            'key_number': k.key_number or None,
            'type': k.key_type, 'state': k.state,
            'state_label': dict(k._fields['state'].selection).get(k.state, k.state),
            'hub': k.key_hub_id.name if k.key_hub_id else None,
            'hub_id': k.key_hub_id.id if k.key_hub_id else None,
            'unit': k.unit_id.name if k.unit_id else None,
            'premise': k.premise_id.name if ('premise_id' in k._fields and k.premise_id) else None,
            'holder': holder.name if holder else None,
            'holder_id': holder.id if holder else None,
            'checkout_time': str(k.check_out_time or '')[:16] or None,
            'expected_return': str(k.expected_return_time or '')[:16] or None,
            'has_nfc': bool(k.nfc_uid), 'has_qr': bool(k.qr_code_text),
        }
        try:
            d['overdue'] = (k.days_overdue or 0) if 'days_overdue' in k._fields else 0
        except Exception:
            d['overdue'] = 0
        if with_log:
            d['log'] = [{
                'id': l.id,
                'operation': l.operation,
                'operation_label': dict(l._fields['operation'].selection).get(l.operation, l.operation),
                'by': l.security_employee_id.name if l.security_employee_id else None,
                'at': str(l.timestamp or '')[:16],
                'expected_return': str(l.expected_return or '')[:16] or None,
                'reason': l.reason or None,
            } for l in k.log_ids.sorted(key=lambda x: (x.timestamp or fields.Datetime.now()), reverse=True)[:50]]
        return d

    def _my_sec_emp(self, env):
        return env['security.employee'].sudo().search([('employee_id.user_id', '=', env.uid)], limit=1)

    @route(API + '/security/keys/board', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def keys_board(self, tab=None, q=None, hub=None, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'security.key' not in env:
            return _ok({'items': [], 'stats': {}})
        K = env['security.key'].sudo()
        dom = []
        if tab in ('available', 'checked_out', 'lost', 'maintenance'):
            dom.append(('state', '=', tab))
        if hub:
            try:
                dom.append(('key_hub_id', '=', int(hub)))
            except (TypeError, ValueError):
                pass
        q = (q or '').strip()
        if q:
            dom += ['|', '|', '|', ('name', 'ilike', q), ('key_number', 'ilike', q),
                    ('door_number', 'ilike', q), ('current_holder_id.name', 'ilike', q)]
        recs = K.search(dom, order='state, name', limit=300)
        return _ok({
            'items': [self._key_full(k) for k in recs],
            'stats': {
                'total': K.search_count([]),
                'available': K.search_count([('state', '=', 'available')]),
                'checked_out': K.search_count([('state', '=', 'checked_out')]),
                'lost': K.search_count([('state', '=', 'lost')]),
            },
        })

    @route(API + '/security/key/meta', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def key_meta(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        hubs = env['security.key.hub'].sudo().search([], order='name') if 'security.key.hub' in env else []
        guards = env['security.employee'].sudo().search([], order='name', limit=300) if 'security.employee' in env else []
        me = self._my_sec_emp(env)
        return _ok({
            'hubs': [{'v': h.id, 'l': h.name} for h in hubs],
            'guards': [{'v': g.id, 'l': g.name, 'badge': g.badge_number or ''} for g in guards],
            'me': {'v': me.id, 'l': me.name} if me else None,
        })

    @route(API + '/security/key/scan', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def key_scan(self, **kw):
        """Resolve a key from a scanned QR/barcode/NFC uid (or a typed key number)."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        b = _body() or {}
        code = (b.get('code') or '').strip()
        if not code:
            return _err('لا يوجد رمز', 422)
        K = env['security.key'].sudo()
        key = K.search(['|', '|', '|', ('nfc_uid', '=', code), ('qr_code_text', '=', code),
                        ('barcode', '=', code), ('key_number', '=', code)], limit=1)
        if not key:
            return _err('لم يتم العثور على مفتاح مطابق', 404)
        return _ok(self._key_full(key, with_log=True))

    @route(API + '/security/key/<int:kid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def key_detail(self, kid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        k = env['security.key'].sudo().browse(kid).exists()
        if not k:
            return _err('غير موجود', 404)
        return _ok(self._key_full(k, with_log=True))

    @route(API + '/security/key/<int:kid>/checkout', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def key_checkout(self, kid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        k = env['security.key'].sudo().browse(kid).exists()
        if not k:
            return _err('المفتاح غير موجود', 404)
        if k.state != 'available':
            return _err('المفتاح غير متاح للصرف', 422)
        b = _body() or {}
        # recipient security employee (defaults to the scanning guard)
        se = env['security.employee'].sudo().browse(int(b['employee_id'])) if b.get('employee_id') else self._my_sec_emp(env)
        if not se:
            return _err('حدّد المستلم', 422)
        import datetime as _dt
        hours = int(b.get('expected_hours') or 8)
        expected = fields.Datetime.now() + _dt.timedelta(hours=hours)
        k.write({
            'state': 'checked_out',
            'current_holder_id': se.employee_id.id,
            'check_out_time': fields.Datetime.now(),
            'expected_return_time': expected,
        })
        env['security.key.log'].sudo().create({
            'key_id': k.id, 'operation': 'check_out', 'security_employee_id': se.id,
            'expected_return': expected, 'reason': (b.get('reason') or '').strip() or False,
        })
        return _ok(self._key_full(k, with_log=True))

    @route(API + '/security/key/<int:kid>/checkin', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def key_checkin(self, kid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        k = env['security.key'].sudo().browse(kid).exists()
        if not k:
            return _err('المفتاح غير موجود', 404)
        if k.state != 'checked_out':
            return _err('المفتاح ليس مصروفاً', 422)
        b = _body() or {}
        se = env['security.employee'].sudo().search([('employee_id', '=', k.current_holder_id.id)], limit=1) or self._my_sec_emp(env)
        vals = {'state': 'available', 'current_holder_id': False,
                'check_out_time': False, 'expected_return_time': False}
        if b.get('hub_id'):  # allow returning to a chosen hub
            try:
                vals['key_hub_id'] = int(b['hub_id'])
            except (TypeError, ValueError):
                pass
        k.write(vals)
        if se:
            try:
                env['security.key.log'].sudo().create({
                    'key_id': k.id, 'operation': 'check_in',
                    'security_employee_id': se.id,
                    'reason': (b.get('notes') or '').strip() or False,
                })
            except Exception:
                pass
        return _ok(self._key_full(k, with_log=True))

    @route(API + '/security/key/<int:kid>/lost', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def key_lost(self, kid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        k = env['security.key'].sudo().browse(kid).exists()
        if not k:
            return _err('المفتاح غير موجود', 404)
        b = _body() or {}
        se = self._my_sec_emp(env)
        k.write({'state': 'lost'})
        if se:
            try:
                env['security.key.log'].sudo().create({
                    'key_id': k.id, 'operation': 'lost', 'security_employee_id': se.id,
                    'reason': (b.get('reason') or '').strip() or 'فُقد'})
            except Exception:
                pass
        return _ok(self._key_full(k, with_log=True))

    # ==== Inspections =====================================================
    def _insp_dict(self, i, full=False):
        F = i._fields

        def _lbl(f):
            try:
                return dict(F[f].selection).get(i[f], i[f]) if f in F and i[f] else None
            except Exception:
                return i[f] if f in F else None
        d = {
            'id': i.id, 'name': i.name,
            'type': _lbl('inspection_type'), 'priority': _lbl('priority'), 'priority_raw': i.priority if 'priority' in F else None,
            'state': i.state, 'state_label': _lbl('state'),
            'issue_type': _lbl('issue_type'), 'severity': _lbl('severity'), 'severity_raw': i.severity if 'severity' in F else None,
            'premise': i.premise_id.name if i.premise_id else None,
            'unit': i.unit_id.name if ('unit_id' in F and i.unit_id) else None,
            'guard': i.guard_id.name if ('guard_id' in F and i.guard_id) else None,
            'assigned_to': i.assigned_to.display_name if ('assigned_to' in F and i.assigned_to) else None,
            'scheduled_date': str(i.scheduled_date or '')[:10] or None,
            'timestamp': str(i.timestamp or '')[:16] or None,
            'description': i.issue_description if 'issue_description' in F else None,
            'has_workorder': bool(i.workorder_id) if 'workorder_id' in F else False,
        }
        if full:
            d['notes'] = i.notes if 'notes' in F else None
            d['resolution_notes'] = i.resolution_notes if 'resolution_notes' in F else None
            d['checklist'] = [{'id': c.id, 'name': c.name if 'name' in c._fields else (c.display_name),
                               'ok': bool(c.is_checked) if 'is_checked' in c._fields else None}
                              for c in i.checklist_item_ids] if 'checklist_item_ids' in F else []
            d['issues'] = [{'id': s.id, 'name': s.display_name} for s in i.issue_ids] if 'issue_ids' in F else []
            d['areas'] = [{'id': a.id, 'name': a.display_name} for a in i.inspection_area_ids] if 'inspection_area_ids' in F else []
        return d

    @route(API + '/security/inspections', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def inspections(self, state=None, q=None, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'security.inspection' not in env:
            return _ok({'items': [], 'stats': {}})
        I = env['security.inspection'].sudo()
        dom = []
        if state and state not in ('all', ''):
            if state == 'open':
                dom.append(('state', 'not in', ('completed', 'cancelled')))
            else:
                dom.append(('state', '=', state))
        q = (q or '').strip()
        if q:
            dom += ['|', '|', ('name', 'ilike', q), ('issue_description', 'ilike', q), ('premise_id.name', 'ilike', q)]
        recs = I.search(dom, order='timestamp desc', limit=200)
        return _ok({
            'items': [self._insp_dict(i) for i in recs],
            'stats': {
                'total': I.search_count([]),
                'open': I.search_count([('state', 'not in', ('completed', 'cancelled'))]),
                'in_progress': I.search_count([('state', '=', 'in_progress')]),
                'completed': I.search_count([('state', '=', 'completed')]),
            },
        })

    @route(API + '/security/inspection/<int:iid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def inspection_detail(self, iid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        i = env['security.inspection'].sudo().browse(iid).exists()
        if not i:
            return _err('غير موجود', 404)
        return _ok(self._insp_dict(i, full=True))

    _INSP_ACTIONS = {'submit': 'action_submit', 'start': 'action_start', 'complete': 'action_complete',
                     'cancel': 'action_cancel', 'reopen': 'action_reopen'}

    @route(API + '/security/inspection/<int:iid>/action', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def inspection_action(self, iid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        i = env['security.inspection'].sudo().browse(iid).exists()
        if not i:
            return _err('غير موجود', 404)
        m = self._INSP_ACTIONS.get((_body() or {}).get('key'))
        if not m or not hasattr(i, m):
            return _err('إجراء غير معروف', 422)
        try:
            getattr(i, m)()
        except Exception as e:
            return _err(str(getattr(e, 'args', [e])[0] if getattr(e, 'args', None) else e), 400)
        return _ok(self._insp_dict(i, full=True))

    @route(API + '/security/inspection/<int:iid>/assign', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def inspection_assign(self, iid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        i = env['security.inspection'].sudo().browse(iid).exists()
        if not i:
            return _err('غير موجود', 404)
        b = _body() or {}
        if not b.get('employee_id'):
            return _err('حدّد الشخص', 422)
        try:
            i.write({'assigned_to': int(b['employee_id'])})
            if hasattr(i, 'action_assign'):
                i.action_assign()
        except Exception as e:
            return _err('تعذّر الإسناد: %s' % e, 400)
        return _ok(self._insp_dict(i, full=True))

    @route(API + '/security/inspection/<int:iid>/to_workorder', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def inspection_to_workorder(self, iid, **kw):
        """Convert an inspection into a work order routed to a chosen service —
        so a maintenance issue found on patrol lands in that service's queue."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        i = env['security.inspection'].sudo().browse(iid).exists()
        if not i:
            return _err('غير موجود', 404)
        if 'care.cafm.workorder' not in env:
            return _err('وحدة أوامر العمل غير متاحة', 404)
        b = _body() or {}
        WO = env['care.cafm.workorder'].sudo()
        vals = {
            'title': 'من تفتيش %s: %s' % (i.name, (i.issue_type or '') if 'issue_type' in i._fields else ''),
            'description': (i.issue_description if 'issue_description' in i._fields else '') or '',
            'priority': {'critical': '3', 'high': '2', 'urgent': '3'}.get(
                i.severity if 'severity' in i._fields else '', '1'),
        }
        fac = getattr(i.premise_id, 'cafm_facility_id', False)
        if fac:
            vals['facility_id'] = fac.id
        Svc = env['care.cafm.service'].sudo()
        svc = Svc.browse(int(b['service_id'])) if b.get('service_id') else Svc.search([], limit=1)
        if svc:
            vals['service_id'] = svc.id
        try:
            wo = WO.create(vals)
            if 'workorder_id' in i._fields:
                i.workorder_id = wo.id
            i.message_post(body='🧾 حُوِّل إلى أمر عمل %s' % wo.display_name)
        except Exception as e:
            return _err('تعذّر التحويل: %s' % e, 400)
        return _ok({'workorder': wo.display_name, 'id': wo.id})

    @route(API + '/security/wo_services', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def wo_services(self, **kw):
        """Services to route a converted work order to + assignable people."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        svcs = env['care.cafm.service'].sudo().search([], limit=100) if 'care.cafm.service' in env else []
        emps = env['hr.employee'].sudo().search([('user_id', '!=', False)], order='name', limit=300)
        return _ok({
            'services': [{'v': s.id, 'l': s.display_name,
                          'type': s.service_type if 'service_type' in s._fields else None} for s in svcs],
            'assignees': [{'v': e.id, 'l': e.name, 'job': e.job_title or None} for e in emps],
        })

    # ==== Emergency / panic alert =========================================
    _SOS = '🚨 بلاغ طوارئ فوري'

    def _team_users(self, env, me):
        """res.users of the guard's fellow team members (to notify)."""
        users = env['res.users']
        if not me or 'security.team' not in env:
            return users
        teams = env['security.team'].sudo().search(
            ['|', ('member_ids', 'in', me.ids), ('leader_id', 'in', me.ids)])
        for t in teams:
            members = t.member_ids | (t.leader_id or env['security.employee'])
            for m in members:
                if m.employee_id and m.employee_id.user_id:
                    users |= m.employee_id.user_id
        return users - env.user

    @route(API + '/security/emergency', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def emergency_raise(self, **kw):
        """Panic button — raise a critical, located incident and push a high-
        priority alert to every fellow team member so they can respond."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'security.incident.report' not in env:
            return _err('غير متاح', 404)
        b = _body() or {}
        I = env['security.incident.report'].sudo()
        prem = env['security.premise'].sudo().search([], limit=1) if 'security.premise' in env else None
        note = (b.get('note') or '').strip()
        vals = {
            'date': fields.Datetime.now(),
            'incident_type': 'other', 'severity': 'critical',
            'reporter_id': env.uid,
            'description': '%s\n%s' % (self._SOS, note or 'حارس بحاجة لمساندة فورية'),
        }
        if prem:
            vals['premise_id'] = prem.id
        me = self._my_sec_emp(env)
        if me and 'guard_id' in I._fields:
            g = env['security.guard'].sudo().search([('user_id', '=', env.uid)], limit=1)
            if g:
                vals['guard_id'] = g.id
        for f, k in (('latitude', 'lat'), ('longitude', 'lng')):
            if b.get(k) and f in I._fields:
                try:
                    vals[f] = float(b[k])
                except (TypeError, ValueError):
                    pass
        rec = I.create(vals)
        # broadcast to the team
        try:
            team = self._team_users(env, me)
            if team and 'care.cafm.notification' in env:
                env['care.cafm.notification'].sudo().push(
                    team, '🚨 نداء استغاثة من زميل', '%s طلب مساندة فورية' % env.user.name,
                    ntype='alert', action_url='/security/emergency/%s' % rec.id)
        except Exception:
            pass
        return _ok({'id': rec.id, 'notified': len(self._team_users(env, me))})

    @route(API + '/security/emergencies', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def emergencies(self, **kw):
        """Active SOS alerts (for the responder map) — critical, located, open."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'security.incident.report' not in env:
            return _ok({'items': []})
        I = env['security.incident.report'].sudo()
        recs = I.search([('description', 'ilike', self._SOS),
                         ('state', 'not in', ('resolved', 'closed'))], order='date desc', limit=50)
        out = []
        for r in recs:
            out.append({
                'id': r.id, 'guard': r.reporter_id.name or None,
                'lat': r.latitude if 'latitude' in r._fields else None,
                'lng': r.longitude if 'longitude' in r._fields else None,
                'at': str(r.date or '')[:16] or None,
                'premise': r.premise_id.name if r.premise_id else None,
                'note': (r.description or '').replace(self._SOS, '').strip() or None,
                'mine': r.reporter_id.id == env.uid,
            })
        return _ok({'items': out})

    @route(API + '/security/emergency/<int:eid>/stop', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def emergency_stop(self, eid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        r = env['security.incident.report'].sudo().browse(eid).exists()
        if not r:
            return _err('غير موجود', 404)
        b = _body() or {}
        if 'resolution_notes' in r._fields and (b.get('reason') or '').strip():
            r.write({'resolution_notes': b['reason'].strip()})
        try:
            if hasattr(r, 'action_resolve'):
                r.action_resolve()
            else:
                r.write({'state': 'resolved'})
        except Exception:
            r.write({'state': 'resolved'})
        return _ok({'stopped': True})

    # ==== إشعار العميل عند بلاغ حرج ======================================
    def _incident_client_users(self, env, inc):
        """مستخدمو العميل المرتبط بموقع البلاغ (منشأة → عميل → مستخدمون)."""
        users = env['res.users']
        try:
            prem = inc.premise_id
            fac = getattr(prem, 'cafm_facility_id', False) if prem else False
            if fac and 'care.cafm.client' in env:
                C = env['care.cafm.client'].sudo()
                client = None
                if getattr(fac, 'partner_id', False):
                    client = C.search([('partner_id', '=', fac.partner_id.id)], limit=1)
                if not client and getattr(fac, 'project_id', False):
                    client = C.search([('project_ids.id', '=', fac.project_id.id)], limit=1)
                if client:
                    users = client.user_ids
        except Exception:
            pass
        return users

    @route(API + '/security/incident/<int:iid>/notify_client', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def incident_notify_client(self, iid, **kw):
        """يُشعر عميل الموقع بالبلاغ (يظهر الزر للبلاغات الحرجة)."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        inc = env['security.incident.report'].sudo().browse(iid).exists()
        if not inc:
            return _err('غير موجود', 404)
        users = self._incident_client_users(env, inc)
        if not users:
            return _err('لا يوجد عميل مرتبط بهذا الموقع', 404)
        try:
            if 'care.cafm.notification' in env:
                env['care.cafm.notification'].sudo().push(
                    users, '⚠️ بلاغ أمني في موقعكم',
                    '%s — %s' % (inc.name, (inc.description or '')[:80]),
                    ntype='alert', action_url='/security/incident/%s' % inc.id)
        except Exception as e:
            return _err('تعذّر الإشعار: %s' % e, 400)
        return _ok({'notified': len(users)})

    # ==== دوريات الحارس (جدولة + حضور بمسح QR/NFC) =======================
    def _my_guard(self, env):
        """سجل الحارس المرتبط بالمستخدم الحالي."""
        return env['security.guard'].sudo().search([('user_id', '=', env.uid)], limit=1)

    def _my_guard_premise(self, env):
        """موقع فريق الحارس الحالي (لبثّ جديد بلا بلاغ). يرجع أول منشأة كحلّ أخير."""
        g = self._my_guard(env)
        if g and g.security_employee_id and g.security_employee_id.team_ids:
            prem = g.security_employee_id.team_ids.mapped('premise_id')
            if prem:
                return prem[0]
        return env['security.premise'].sudo().search([], limit=1) if 'security.premise' in env else None

    def _patrol_dict2(self, p, full=False):
        F = p._fields
        pts = list(p.patrol_point_ids) if 'patrol_point_ids' in F else []
        scanned = set(p.log_ids.mapped('point_id').ids) if 'log_ids' in F else set()
        d = {
            'id': p.id, 'name': p.name, 'state': p.state,
            'state_label': dict(p._fields['state'].selection).get(p.state, p.state),
            'route': p.route_id.name if ('route_id' in F and p.route_id) else None,
            'premise': p.premise_id.name if ('premise_id' in F and p.premise_id) else None,
            'scheduled_start': str(p.scheduled_start or '')[:16] or None,
            'points_total': len(pts), 'points_done': len([1 for pt in pts if pt.id in scanned]),
            'completion': round(p.completion_rate or 0.0, 0) if 'completion_rate' in F else 0,
        }
        if full:
            d['points'] = [{
                'id': pt.id, 'name': pt.name,
                'code': pt.code if 'code' in pt._fields else None,
                'type': pt.point_type if 'point_type' in pt._fields else None,
                'unit': pt.unit_id.name if ('unit_id' in pt._fields and pt.unit_id) else None,
                'scanned': pt.id in scanned,
                'has_nfc': bool(pt.nfc_uid) if 'nfc_uid' in pt._fields else False,
            } for pt in pts]
            d['log'] = [{
                'id': l.id, 'point': l.point_id.name if l.point_id else None,
                'at': str(l.timestamp or '')[:16], 'issue': bool(l.issue_detected) if 'issue_detected' in l._fields else False,
            } for l in p.log_ids.sorted(key=lambda x: (x.timestamp or fields.Datetime.now()), reverse=True)[:50]]
        return d

    @route(API + '/security/my_patrols', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def my_patrols(self, **kw):
        """دوريات الحارس الحالي (مجدولة/جارية/منتهية حديثاً)."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'security.patrol' not in env:
            return _ok({'items': [], 'stats': {}})
        P = env['security.patrol'].sudo()
        g = self._my_guard(env)
        dom = [('guard_id', '=', g.id)] if g else [('id', '=', 0)]
        recs = P.search(dom, order='scheduled_start desc', limit=60)
        return _ok({
            'items': [self._patrol_dict2(p) for p in recs],
            'stats': {
                'scheduled': P.search_count(dom + [('state', '=', 'scheduled')]),
                'in_progress': P.search_count(dom + [('state', '=', 'in_progress')]),
                'completed': P.search_count(dom + [('state', '=', 'completed')]),
            },
        })

    @route(API + '/security/patrol/<int:pid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def patrol_detail(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        p = env['security.patrol'].sudo().browse(pid).exists()
        if not p:
            return _err('غير موجود', 404)
        return _ok(self._patrol_dict2(p, full=True))

    @route(API + '/security/patrol/<int:pid>/start', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def patrol_start(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        p = env['security.patrol'].sudo().browse(pid).exists()
        if not p:
            return _err('غير موجود', 404)
        try:
            if hasattr(p, 'action_start'):
                p.action_start()
            else:
                p.write({'state': 'in_progress', 'start_time': fields.Datetime.now()})
        except Exception as e:
            return _err(str(getattr(e, 'args', [e])[0] if getattr(e, 'args', None) else e), 400)
        return _ok(self._patrol_dict2(p, full=True))

    @route(API + '/security/patrol/<int:pid>/complete', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def patrol_complete(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        p = env['security.patrol'].sudo().browse(pid).exists()
        if not p:
            return _err('غير موجود', 404)
        try:
            if hasattr(p, 'action_complete'):
                p.action_complete()
            else:
                p.write({'state': 'completed', 'end_time': fields.Datetime.now()})
        except Exception as e:
            return _err(str(getattr(e, 'args', [e])[0] if getattr(e, 'args', None) else e), 400)
        return _ok(self._patrol_dict2(p, full=True))

    @route(API + '/security/patrol/scan', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def patrol_scan(self, **kw):
        """مسح نقطة تفتيش (QR/NFC) أثناء دورية جارية — إثبات الحضور."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        b = _body() or {}
        code = (b.get('code') or '').strip()
        pid = b.get('patrol_id')
        if not code or not pid:
            return _err('الرمز ومعرّف الدورية مطلوبان', 422)
        Point = env['security.patrol.point'].sudo()
        try:
            res = Point.process_checkpoint_scan(code, int(pid))
        except Exception as e:
            return _err('تعذّر تسجيل المسح: %s' % e, 400)
        # process_checkpoint_scan قد يُرجع dict فيه success/error
        if isinstance(res, dict) and res.get('error'):
            return _err(res.get('error'), 422)
        p = env['security.patrol'].sudo().browse(int(pid)).exists()
        return _ok({'result': res if isinstance(res, dict) else {'success': True},
                    'patrol': self._patrol_dict2(p, full=True) if p else None})

    # ==== البث المباشر عبر مزوّدات خارجية =================================
    @route(API + '/security/stream/providers', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def stream_providers(self, **kw):
        """المزوّدات المفعّلة (للتطبيق ليختار منها). لا تُرسل الأسرار."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.stream.provider' not in env:
            return _ok({'providers': []})
        provs = env['care.stream.provider'].sudo().search([('active', '=', True)])
        return _ok({'providers': [{
            'id': p.id, 'name': p.name, 'type': p.provider_type,
            'requires_token': p.requires_token,
        } for p in provs]})

    # الإبقاء على config للتوافق مع النسخ القديمة (يشير الآن لوجود مزوّدات)
    @route(API + '/security/stream/config', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def stream_config(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        n = env['care.stream.provider'].sudo().search_count([('active', '=', True)]) if 'care.stream.provider' in env else 0
        return _ok({'enabled': n > 0, 'providers': n})

    # ---- مساعدو الجلسات ---------------------------------------------------
    def _live_session(self, env, iid):
        """جلسة البثّ المباشرة الحالية لبلاغٍ ما (إن وُجدت)."""
        if 'care.stream.session' not in env:
            return None
        return env['care.stream.session'].sudo().search(
            [('incident_id', '=', int(iid)), ('state', '=', 'live')],
            order='id desc', limit=1) or None

    def _session_info(self, s, role='audience'):
        """لقطة كاملة عن جلسة البثّ لعرضها في الشاشات."""
        started = s.started_at
        return {
            'session_id': s.id, 'channel': s.name, 'incident_id': s.incident_id,
            'role': role, 'live': s.state == 'live',
            'guard': s.guard_name or (s.guard_user_id.name if s.guard_user_id else None),
            'guard_user_id': s.guard_user_id.id if s.guard_user_id else None,
            'premise': s.premise_name, 'client': s.client_name,
            'audience': s.audience,
            'provider': s.provider_id.name if s.provider_id else None,
            'provider_type': s.provider_id.provider_type if s.provider_id else None,
            'started_at': str(started or '')[:19] or None,
            'viewer_count': s.viewer_count, 'peak_viewers': s.peak_viewers,
            'latitude': s.latitude or None, 'longitude': s.longitude or None,
            # الروابط بحسب الدور: الباثّ يحتاج whip، المشاهد يحتاج whep/hls
            'whip_url': s.whip_url if role == 'broadcaster' else None,
            'whep_url': s.whep_url or None,
            'playback_url': s.playback_url or None,
            'ingest_url': s.ingest_url if role == 'broadcaster' else None,
        }

    @route(API + '/security/stream/start', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def stream_start(self, **kw):
        """الحارس يبدأ بثاً: يختار مزوّداً فيولّد الخادم روابط النشر/المشاهدة
        (WebRTC WHIP/WHEP + HLS)، تُنشأ جلسة بثّ تحمل لقطة كاملة (الحارس/الموقع/
        العميل/الموقع الجغرافي)، ثم يُشعَر المشاهدون المختارون."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        b = _body() or {}
        I = env['security.incident.report'].sudo()
        inc = I.browse(int(b['incident_id'])).exists() if b.get('incident_id') else None
        if not inc:
            # بثّ جديد بلا بلاغ: يُنشأ على موقع فريق الحارس، لا أول موقع عشوائي
            prem = self._my_guard_premise(env)
            inc = I.create({
                'incident_type': 'other', 'severity': 'high', 'reporter_id': env.uid,
                'description': '🎥 بث مباشر',
                'premise_id': prem.id if prem else False,
            }) if 'security.premise' in env else None
            if not inc:
                return _err('تعذّر بدء البث', 400)
        channel = 'care_%s' % inc.id
        urls = {'ingest_url': '', 'playback_url': '', 'whip_url': '', 'whep_url': ''}
        prov = None
        cf_uid = None
        if 'care.stream.provider' in env:
            P = env['care.stream.provider'].sudo()
            prov = P.browse(int(b['provider_id'])).exists() if b.get('provider_id') else P.search([('active', '=', True)], limit=1)
            if prov:
                # قناة ديناميكية عبر Cloudflare API (بثوث متزامنة)، أو القالب الثابت
                cf = prov._cf_create_input(channel)
                if cf:
                    urls = {k: cf[k] for k in ('ingest_url', 'playback_url', 'whip_url', 'whep_url')}
                    cf_uid = cf['input_uid']
                else:
                    import hashlib
                    key = hashlib.sha1(('%s-%s' % (channel, prov.api_key or '')).encode()).hexdigest()[:12]
                    urls = prov._build_urls(channel, key)
        if not urls['playback_url'] and (b.get('url') or '').strip():
            urls['playback_url'] = b['url'].strip()

        # لقطة الموقع/العميل/الحارس
        guard = self._my_guard(env) if hasattr(self, '_my_guard') else None
        guard_name = (guard.security_employee_id.name if guard and guard.security_employee_id else None) or env.user.name
        premise_name = inc.premise_id.name if inc.premise_id else None
        client_name = inc.premise_id.client_id.name if (inc.premise_id and inc.premise_id.client_id) else None

        # ننهي أي جلسة سابقة لنفس البلاغ ثم ننشئ الجديدة
        if 'care.stream.session' in env:
            old = env['care.stream.session'].sudo().search([('incident_id', '=', inc.id), ('state', '=', 'live')])
            if old:
                old._end()
        audience = b.get('audience') or 'all'
        if audience not in ('all', 'client', 'team'):
            audience = 'all'
        session = env['care.stream.session'].sudo().create({
            'name': channel, 'incident_id': inc.id,
            'provider_id': prov.id if prov else False,
            'guard_user_id': env.uid, 'guard_name': guard_name,
            'premise_name': premise_name, 'client_name': client_name,
            'ingest_url': urls['ingest_url'], 'playback_url': urls['playback_url'],
            'whip_url': urls['whip_url'], 'whep_url': urls['whep_url'],
            'cf_input_uid': cf_uid or False, 'audience': audience,
            'latitude': float(b.get('latitude') or 0.0), 'longitude': float(b.get('longitude') or 0.0),
        }) if 'care.stream.session' in env else None

        if 'live_active' in inc._fields:
            inc.write({'live_active': True})

        # إشعار الجمهور حسب اختيار الحارس: العميل فقط / الفريق فقط / الكل
        try:
            targets = env['res.users']
            if audience in ('all', 'team'):
                ids = b.get('viewer_ids') or []
                targets |= env['res.users'].sudo().browse([int(i) for i in ids]).exists() if ids else self._team_users(env, self._my_sec_emp(env))
            if audience in ('all', 'client') and inc:
                targets |= self._incident_client_users(env, inc)
            if targets and 'care.cafm.notification' in env:
                env['care.cafm.notification'].sudo().push(
                    targets, '🎥 بث مباشر من حارس',
                    '%s يبثّ الآن من %s' % (guard_name, premise_name or 'الموقع'),
                    ntype='alert', action_url='/security/stream/%s' % inc.id)
        except Exception:
            pass

        out = self._session_info(session, 'broadcaster') if session else {}
        out.update({'channel': channel, 'incident_id': inc.id, 'role': 'broadcaster',
                    'ingest_url': urls['ingest_url'], 'playback_url': urls['playback_url'],
                    'whip_url': urls['whip_url'], 'whep_url': urls['whep_url'],
                    'provider': prov.name if prov else None,
                    'provider_type': prov.provider_type if prov else None,
                    'supports_webrtc': bool(urls['whip_url'])})
        return _ok(out)

    @route(API + '/security/stream/stop', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def stream_stop(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        b = _body() or {}
        iid = int(b['incident_id']) if b.get('incident_id') else 0
        s = self._live_session(env, iid)
        if s:
            s._end()
        inc = env['security.incident.report'].sudo().browse(iid).exists() if iid else None
        if inc and 'live_active' in inc._fields:
            inc.write({'live_active': False})
        return _ok({'stopped': True})

    @route(API + '/security/stream/watch/<int:iid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def stream_watch(self, iid, **kw):
        """مشاهد ينضم لبث بلاغ — يُسجَّل مشاهداً ويُرجع روابط المشاهدة وبياناتها."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        s = self._live_session(env, iid)
        if not s:
            return _ok({'live': False, 'channel': 'care_%s' % iid, 'role': 'audience'})
        s._join(env.user)
        info = self._session_info(s, 'audience')
        # للتوافق مع النسخ القديمة: url = أفضل رابط مشاهدة متاح
        info['url'] = s.whep_url or s.playback_url or ''
        return _ok(info)

    @route(API + '/security/stream/leave/<int:iid>', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def stream_leave(self, iid, **kw):
        """مشاهد يغادر البث (لتحديث العدّاد لدى الحارس)."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        s = self._live_session(env, iid)
        if s:
            s._leave(env.user)
        return _ok({'left': True})

    @route(API + '/security/stream/viewers/<int:iid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def stream_viewers(self, iid, **kw):
        """قائمة المشاهدين الحاليين + العدّاد (تُحدَّث دورياً لدى الحارس)."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        s = self._live_session(env, iid)
        if not s:
            return _ok({'live': False, 'count': 0, 'viewers': []})
        vs = s.viewer_ids.filtered('active').sorted(key=lambda v: v.joined_at or fields.Datetime.now(), reverse=True)
        return _ok({
            'live': True, 'count': len(vs), 'peak': s.peak_viewers,
            'viewers': [{
                'user_id': v.user_id.id if v.user_id else None,
                'name': v.user_name or (v.user_id.name if v.user_id else 'مشاهد'),
                'since': str(v.joined_at or '')[11:16],
            } for v in vs],
        })

    @route(API + '/security/stream/info/<int:iid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def stream_info(self, iid, **kw):
        """بيانات البث الكاملة لبلاغٍ (للحالة/الأيقونة/الشاشة)."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        s = self._live_session(env, iid)
        if not s:
            return _ok({'live': False, 'incident_id': iid})
        return _ok(self._session_info(s, 'audience'))

    # ==== بانر البثوث الحيّة (للرئيسية) =====================================
    @route(API + '/security/stream/active', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def stream_active(self, **kw):
        """البثوث الحيّة الحالية (لبانر الرئيسية) — اسم وصورة الباثّ + الحالة."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.stream.session' not in env:
            return _ok({'items': []})
        # الفريق يرى البثوث الموجَّهة له (الكل/الفريق) + بثوثه هو، لا «العميل فقط»
        sess = env['care.stream.session'].sudo().search(
            ['&', ('state', '=', 'live'), ('kind', '=', 'main'),
             '|', ('audience', 'in', ('all', 'team')), ('guard_user_id', '=', env.uid)],
            order='id desc', limit=20)
        items = []
        for s in sess:
            items.append({
                'incident_id': s.incident_id, 'session_id': s.id,
                'guard': s.guard_name, 'guard_photo': self._user_photo(env, s.guard_user_id),
                'premise': s.premise_name, 'client': s.client_name,
                'viewer_count': s.viewer_count,
                'started_at': str(s.started_at or '')[:19] or None,
                'is_mine': s.guard_user_id.id == env.uid,
                'cohosts': len(s.cohost_ids.filtered(lambda c: c.state == 'live')),
            })
        return _ok({'items': items, 'count': len(items)})

    def _user_photo(self, env, user):
        """صورة مصغّرة (base64) للمستخدم لعرضها في البانر."""
        if not user:
            return None
        try:
            img = user.image_128 or (user.partner_id.image_128 if user.partner_id else False)
            return img.decode() if img and isinstance(img, bytes) else (img or None)
        except Exception:
            return None

    # ==== سجل البثّ (الأرشيف + التسجيلات) =================================
    def _archive_dict(self, s):
        dur = 0
        if s.started_at and s.ended_at:
            dur = int((s.ended_at - s.started_at).total_seconds())
        return {
            'session_id': s.id, 'incident_id': s.incident_id,
            'guard': s.guard_name, 'premise': s.premise_name, 'client': s.client_name,
            'provider': s.provider_id.name if s.provider_id else None,
            'started_at': str(s.started_at or '')[:19] or None,
            'ended_at': str(s.ended_at or '')[:19] or None,
            'duration': dur, 'peak_viewers': s.peak_viewers, 'total_viewers': s.total_viewers,
            'latitude': s.latitude or None, 'longitude': s.longitude or None,
            'has_recording': s.has_recording,
            'recording_url': s.recording_url or None,
            'thumbnail': s.recording_thumbnail or None,
            'audience': s.audience,
        }

    @route(API + '/security/stream/archive', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def stream_archive(self, **kw):
        """سجل كل البثوث المنتهية بتفاصيلها + تسجيلاتها لإعادة التشغيل."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.stream.session' not in env:
            return _ok({'items': []})
        sess = env['care.stream.session'].sudo().search(
            [('state', '=', 'ended'), ('kind', '=', 'main')], order='id desc', limit=60)
        try:
            sess._fetch_recording()  # جلب VOD كسولاً من Cloudflare
        except Exception:
            pass
        return _ok({'items': [self._archive_dict(s) for s in sess]})

    @route(API + '/security/stream/archive/<int:sid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def stream_archive_detail(self, sid, **kw):
        """تفاصيل بثّ مؤرشف + رابط تسجيله + دردشته."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        s = env['care.stream.session'].sudo().browse(sid).exists()
        if not s:
            return _err('غير موجود', 404)
        try:
            s._fetch_recording()
        except Exception:
            pass
        d = self._archive_dict(s)
        d['messages'] = [{
            'name': m.user_name or 'مستخدم', 'body': m.body, 'kind': m.kind,
            'is_client': m.is_client, 'at': str(m.created_at or '')[11:16],
        } for m in s.message_ids]
        d['viewers_list'] = [{'name': v.user_name, 'joined': str(v.joined_at or '')[11:16]} for v in s.viewer_ids]
        return _ok(d)

    # ==== الدردشة الحيّة على البثّ =========================================
    @route(API + '/security/stream/<int:iid>/message', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def stream_message_post(self, iid, **kw):
        """إرسال رسالة دردشة على بثّ بلاغٍ (الفريق/العميل)."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        s = self._live_session(env, iid)
        if not s:
            return _err('لا يوجد بثّ مباشر', 404)
        body = (_body().get('body') or '').strip()
        if not body:
            return _err('رسالة فارغة', 400)
        m = env['care.stream.message'].sudo().create({
            'session_id': s.id, 'incident_id': iid, 'user_id': env.uid,
            'user_name': env.user.name, 'body': body[:500], 'kind': 'chat',
        })
        return _ok({'id': m.id})

    @route(API + '/security/stream/<int:iid>/messages', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def stream_messages(self, iid, after=0, **kw):
        """رسائل الدردشة (مع after=<id> لجلب الجديد فقط عبر الاستطلاع)."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        s = self._live_session(env, iid)
        if not s:
            return _ok({'live': False, 'messages': []})
        dom = [('session_id', '=', s.id)]
        try:
            if int(after or 0) > 0:
                dom.append(('id', '>', int(after)))
        except Exception:
            pass
        msgs = env['care.stream.message'].sudo().search(dom, order='id asc', limit=100)
        return _ok({'live': True, 'messages': [{
            'id': m.id, 'name': m.user_name or 'مستخدم', 'body': m.body,
            'kind': m.kind, 'is_client': m.is_client,
            'mine': m.user_id.id == env.uid,
            'at': str(m.created_at or '')[11:16],
        } for m in msgs]})

    # ==== المشاركة في البثّ (co-host) =====================================
    @route(API + '/security/stream/<int:iid>/cohost/start', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def stream_cohost_start(self, iid, **kw):
        """عضو فريق يشارك في البثّ: تُنشأ جلسة فرعية بقناته الخاصة تظهر كـ PiP.
        يتطلّب مزوّداً يدعم قنوات متعددة (WebRTC). يُرجع رابط النشر الخاص به."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        main = self._live_session(env, iid)
        if not main:
            return _err('لا يوجد بثّ رئيسي مباشر', 404)
        prov = main.provider_id
        if not prov or not prov.supports_webrtc:
            return _err('المزوّد لا يدعم المشاركة في البثّ', 400)
        b = _body() or {}
        channel = 'care_%s_co_%s' % (iid, env.uid)
        # قناة ديناميكية للمشارك (تتيح مشاركة متزامنة حقيقية)، أو القالب الثابت
        cf_uid = None
        cf = prov._cf_create_input(channel)
        if cf:
            urls = {k: cf[k] for k in ('ingest_url', 'playback_url', 'whip_url', 'whep_url')}
            cf_uid = cf['input_uid']
        else:
            import hashlib
            key = hashlib.sha1(('%s-%s' % (channel, prov.api_key or '')).encode()).hexdigest()[:12]
            urls = prov._build_urls(channel, key)
        guard = self._my_guard(env) if hasattr(self, '_my_guard') else None
        gname = (guard.security_employee_id.name if guard and guard.security_employee_id else None) or env.user.name
        # ننهي أي مشاركة سابقة لنفس العضو
        old = env['care.stream.session'].sudo().search(
            [('parent_id', '=', main.id), ('guard_user_id', '=', env.uid), ('state', '=', 'live')])
        if old:
            old._end()
        co = env['care.stream.session'].sudo().create({
            'name': channel, 'incident_id': iid, 'kind': 'cohost', 'parent_id': main.id,
            'provider_id': prov.id, 'guard_user_id': env.uid, 'guard_name': gname,
            'premise_name': main.premise_name, 'client_name': main.client_name,
            'whip_url': urls['whip_url'], 'whep_url': urls['whep_url'],
            'playback_url': urls['playback_url'], 'ingest_url': urls['ingest_url'],
            'cf_input_uid': cf_uid or False,
            'latitude': float(b.get('latitude') or 0.0), 'longitude': float(b.get('longitude') or 0.0),
        })
        env['care.stream.message'].sudo().create({
            'session_id': main.id, 'incident_id': iid, 'user_id': env.uid,
            'user_name': gname, 'body': '%s شارك في البثّ' % gname, 'kind': 'system',
        })
        return _ok({'session_id': co.id, 'channel': channel, 'role': 'cohost',
                    'whip_url': urls['whip_url'], 'supports_webrtc': bool(urls['whip_url'])})

    @route(API + '/security/stream/<int:iid>/cohost/stop', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def stream_cohost_stop(self, iid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        main = self._live_session(env, iid)
        if main:
            co = env['care.stream.session'].sudo().search(
                [('parent_id', '=', main.id), ('guard_user_id', '=', env.uid), ('state', '=', 'live')])
            if co:
                co._end()
        return _ok({'stopped': True})

    @route(API + '/security/stream/<int:iid>/cohosts', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def stream_cohosts(self, iid, **kw):
        """المشاركون الأحياء في بثّ بلاغٍ (لعرض PiP في العارض)."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        main = self._live_session(env, iid)
        if not main:
            return _ok({'cohosts': []})
        cos = main.cohost_ids.filtered(lambda c: c.state == 'live')
        return _ok({'cohosts': [{
            'session_id': c.id, 'guard': c.guard_name,
            'whep_url': c.whep_url or None, 'playback_url': c.playback_url or None,
            'is_mine': c.guard_user_id.id == env.uid,
        } for c in cos]})

    # ==== Gate passes =====================================================
    def _gp_dict(self, g, full=False):
        F = g._fields

        def _lbl(f):
            try:
                return dict(F[f].selection).get(g[f], g[f]) if f in F and g[f] else None
            except Exception:
                return g[f] if f in F else None
        d = {
            'id': g.id, 'name': g.name,
            'visitor': g.visitor_name if 'visitor_name' in F else (g.visitor_id.name if g.visitor_id else None),
            'type': _lbl('pass_type'), 'state': g.state, 'state_label': _lbl('state'),
            'premise': g.premise_id.name if g.premise_id else None,
            'valid_until': str(g.valid_until or '')[:16] or None,
            'checked_in': bool(g.checked_in) if 'checked_in' in F else False,
            'checked_out': bool(g.checked_out) if 'checked_out' in F else False,
            'plate': g.license_plate if ('license_plate' in F and g.license_plate) else None,
        }
        if full:
            d.update({
                'visitor_phone': g.visitor_phone if 'visitor_phone' in F else None,
                'visitor_company': g.visitor_company if 'visitor_company' in F else None,
                'purpose': g.purpose if 'purpose' in F else None,
                'valid_from': str(g.valid_from or '')[:16] or None,
                'host': g.host_id.display_name if ('host_id' in F and g.host_id) else None,
                'escort': g.escort_id.display_name if ('escort_id' in F and g.escort_id) else None,
                'require_escort': bool(g.require_escort) if 'require_escort' in F else False,
                'check_in_time': str(g.check_in_time or '')[:16] or None,
                'check_out_time': str(g.check_out_time or '')[:16] or None,
                'approved_by': g.approved_by.name if ('approved_by' in F and g.approved_by) else None,
                'rejection_reason': g.rejection_reason if ('rejection_reason' in F and g.rejection_reason) else None,
            })
        return d

    @route(API + '/security/gatepasses/board', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def gatepasses_board(self, state=None, q=None, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'security.gate.pass' not in env:
            return _ok({'items': [], 'stats': {}})
        G = env['security.gate.pass'].sudo()
        dom = []
        if state and state not in ('all', ''):
            if state == 'onsite':
                dom += [('checked_in', '=', True), ('checked_out', '=', False)]
            else:
                dom.append(('state', '=', state))
        q = (q or '').strip()
        if q:
            dom += ['|', '|', ('name', 'ilike', q), ('visitor_name', 'ilike', q), ('license_plate', 'ilike', q)]
        recs = G.search(dom, order='valid_from desc', limit=200)
        return _ok({
            'items': [self._gp_dict(g) for g in recs],
            'stats': {
                'total': G.search_count([]),
                'pending': G.search_count([('state', '=', 'pending')]),
                'approved': G.search_count([('state', 'in', ('approved', 'valid'))]),
                'onsite': G.search_count([('checked_in', '=', True), ('checked_out', '=', False)]),
            },
        })

    @route(API + '/security/gatepass/<int:gid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def gatepass_detail(self, gid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = env['security.gate.pass'].sudo().browse(gid).exists()
        if not g:
            return _err('غير موجود', 404)
        return _ok(self._gp_dict(g, full=True))

    _GP_ACTIONS = {'submit': 'action_submit', 'approve': 'action_approve', 'reject': 'action_reject',
                   'cancel': 'action_cancel', 'checkin': 'action_check_in', 'checkout': 'action_check_out'}

    @route(API + '/security/gatepass/<int:gid>/action', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def gatepass_action(self, gid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = env['security.gate.pass'].sudo().browse(gid).exists()
        if not g:
            return _err('غير موجود', 404)
        b = _body() or {}
        m = self._GP_ACTIONS.get(b.get('key'))
        if not m or not hasattr(g, m):
            return _err('إجراء غير معروف', 422)
        if b.get('key') == 'reject' and (b.get('reason') or '').strip() and 'rejection_reason' in g._fields:
            g.write({'rejection_reason': b['reason'].strip()})
        try:
            getattr(g, m)()
        except Exception as e:
            return _err(str(getattr(e, 'args', [e])[0] if getattr(e, 'args', None) else e), 400)
        return _ok(self._gp_dict(g, full=True))

    @route(API + '/security/gatepass/scan', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def gatepass_scan(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        code = ((_body() or {}).get('code') or '').strip()
        if not code:
            return _err('لا يوجد رمز', 422)
        g = env['security.gate.pass'].sudo().search(
            ['|', '|', ('qr_code_text', '=', code), ('barcode', '=', code), ('name', '=', code)], limit=1)
        if not g:
            return _err('لم يتم العثور على تصريح', 404)
        return _ok(self._gp_dict(g, full=True))

    @route(API + '/security/incident/meta', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def incident_meta(self, **kw):
        """Options for the incident create form (premises, guards, teams, and the
        type/severity selections) — mirrors the backend Incident Report form."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        I = env['security.incident.report'].sudo()

        def _sel(field):
            try:
                return [{'v': k, 'l': v} for k, v in I._fields[field]._description_selection(env)]
            except Exception:
                return []
        def _opts(model, name_field='name', order='name'):
            if model not in env:
                return []
            out = []
            for r in env[model].sudo().search([], order=order, limit=300):
                try:
                    label = getattr(r, name_field, False) or r.display_name
                except Exception:
                    label = 'ID %s' % r.id
                out.append({'v': r.id, 'l': label})
            return out
        return _ok({
            'types': _sel('incident_type'),
            'severities': _sel('severity'),
            'premises': _opts('security.premise', 'name'),
            'guards': _opts('security.guard', 'name'),
            'teams': _opts('security.team', 'name'),
        })

    @route(API + '/security/incidents', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def incidents(self, q=None, state=None, offset=None, limit=None, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        I = env['security.incident.report'].sudo()
        dom = []
        q = (q or '').strip()
        if q:
            dom += ['|', '|', ('name', 'ilike', q), ('description', 'ilike', q), ('location', 'ilike', q)]
        if state and state != 'all':
            if state == 'open':
                dom.append(('state', 'not in', ('resolved', 'closed')))
            else:
                dom.append(('state', '=', state))
        try:
            offset = int(offset or 0)
            limit = min(int(limit or 30), 100)
        except (TypeError, ValueError):
            offset, limit = 0, 30
        total = I.search_count(dom)
        recs = I.search(dom, order='date desc', offset=offset, limit=limit)
        # header stats (unfiltered by q so the counts stay stable)
        stats = {
            'total': I.search_count([]),
            'open': I.search_count([('state', 'not in', ('resolved', 'closed'))]),
            'critical': I.search_count([('severity', '=', 'critical'), ('state', 'not in', ('resolved', 'closed'))]),
            'resolved': I.search_count([('state', 'in', ('resolved', 'closed'))]),
        }
        return _ok({'items': [_incident_dict(i) for i in recs], 'total': total,
                    'offset': offset, 'limit': limit, 'stats': stats})

    @route(API + '/security/incidents', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def incident_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        b = _body()
        Premise = env['security.premise'].sudo()
        # موقع الحارس من فريقه بدل أول موقع عشوائي (برج جاسم)
        premise = Premise.browse(int(b['premise_id'])) if b.get('premise_id') else self._my_guard_premise(env)
        if not premise:
            return _err('لا يوجد موقع أمني مُعرّف', 422)
        desc = (b.get('description') or '').strip()
        if not desc:
            return _err('description مطلوب', 422)
        Incident = env['security.incident.report'].sudo()
        F = Incident._fields
        vals = {
            'date': b.get('date') or fields.Datetime.now(),
            'premise_id': premise.id,
            'incident_type': b.get('type') or 'other',
            'severity': b.get('severity') or 'medium',
            'description': desc,
            'reporter_id': env.user.id,
        }
        # optional full-form fields (mirror the Incident Report form)
        if b.get('location') and 'location' in F:
            vals['location'] = b['location']
        if b.get('action_taken') and 'action_taken' in F:
            vals['action_taken'] = b['action_taken']
        for fk, key in (('guard_id', 'guard_id'), ('team_id', 'team_id'), ('patrol_id', 'patrol_id')):
            if b.get(key) and fk in F:
                try:
                    vals[fk] = int(b[key])
                except (TypeError, ValueError):
                    pass
        if 'police_notified' in F and b.get('police_notified') is not None:
            vals['police_notified'] = bool(b.get('police_notified'))
        if b.get('police_report_number') and 'police_report_number' in F:
            vals['police_report_number'] = b['police_report_number']
        if 'follow_up_required' in F and b.get('follow_up_required') is not None:
            vals['follow_up_required'] = bool(b.get('follow_up_required'))
        if b.get('follow_up_notes') and 'follow_up_notes' in F:
            vals['follow_up_notes'] = b['follow_up_notes']
        if b.get('lat') and b.get('lng') and 'latitude' in F:
            try:
                vals['latitude'] = float(b['lat']); vals['longitude'] = float(b['lng'])
            except (TypeError, ValueError):
                pass
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

        def _lbl(field, code):
            try:
                return dict(i._fields[field]._description_selection(env)).get(code)
            except Exception:
                return code

        return _ok({
            'id': i.id, 'name': i.name,
            'type': i.incident_type, 'type_label': _lbl('incident_type', i.incident_type),
            'severity': i.severity, 'severity_label': _lbl('severity', i.severity),
            'state': i.state, 'state_label': _lbl('state', i.state),
            'date': str(i.date or '')[:16] or None,
            'reporter': i.reporter_id.name or None,
            'premise': i.premise_id.name or None,
            'location': i.location or None,
            'located': i.located, 'map_url': i.map_url or None,
            'lat': i.latitude, 'lng': i.longitude,
            'description': i.description or None,
            'action_taken': i.action_taken or None,
            # responders
            'guard': i.guard_id.name or None,
            'team': i.team_id.name or None,
            'patrol': i.patrol_id.name or None,
            'witnesses': [w.name for w in i.witness_ids] if 'witness_ids' in i._fields else [],
            'involved': [p.name for p in i.involved_person_ids] if 'involved_person_ids' in i._fields else [],
            # police
            'police_notified': i.police_notified,
            'police_report_number': i.police_report_number or None,
            # resolution + follow-up
            'resolution_date': str(i.resolution_date or '')[:16] or None,
            'resolution_notes': i.resolution_notes or None,
            'follow_up_required': i.follow_up_required if 'follow_up_required' in i._fields else False,
            'follow_up_date': str(i.follow_up_date or '')[:10] or None if 'follow_up_date' in i._fields else None,
            'follow_up_notes': i.follow_up_notes or None if 'follow_up_notes' in i._fields else None,
            'live_active': i.live_active, 'live_url': i.live_url or None,
            'workorder': i.workorder_id.display_name or None,
            'media': [{
                'id': m.id, 'kind': m.kind, 'caption': m.name or None,
                'url': '%s/web/image/security.incident.media/%s/file' % (base, m.id),
                'at': str(m.taken_at or '')[:16], 'by': m.user_id.name or None,
            } for m in i.media_ids],
            'updates': [{
                'id': u.id, 'body': u.body, 'by': u.user_id.name or None,
                'at': str(u.at or '')[:16],
            } for u in i.update_ids],
        })

    @route(API + '/security/incident/media/<int:mid>/raw', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def incident_media_raw(self, mid, **kw):
        """Stream a media file for the app (token via ?token= so <Image> can load
        it — /web/image needs a web session the token app doesn't have)."""
        env = _auth()
        if not env:
            return request.not_found()
        m = env['security.incident.media'].sudo().browse(mid).exists()
        if not m or not m.file:
            return request.not_found()
        import base64
        try:
            data = base64.b64decode(m.file)
        except Exception:
            return request.not_found()
        mimetype = 'video/mp4' if m.kind == 'video' else 'image/jpeg'
        return request.make_response(data, headers=[
            ('Content-Type', mimetype), ('Content-Disposition', 'inline'),
            ('Cache-Control', 'private, max-age=3600')])

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

    # workflow: report / investigate / resolve / close / reset / police
    _INC_ACTIONS = {
        'report': 'action_report', 'investigate': 'action_investigate',
        'resolve': 'action_resolve', 'close': 'action_close',
        'reset': 'action_reset_to_draft', 'police': 'action_notify_police',
    }

    @route(API + '/security/incident/<int:iid>/action', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def incident_action(self, iid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        i = env['security.incident.report'].sudo().browse(iid).exists()
        if not i:
            return _err('غير موجود', 404)
        b = _body() or {}
        key = b.get('key')
        method = self._INC_ACTIONS.get(key)
        if not method or not hasattr(i, method):
            return _err('إجراء غير معروف', 422)
        # optional side data before running the transition
        if key in ('resolve', 'close') and (b.get('resolution_notes') or '').strip():
            if 'resolution_notes' in i._fields:
                i.write({'resolution_notes': b['resolution_notes'].strip()})
        if key == 'police' and (b.get('police_report_number') or '').strip():
            i.write({'police_report_number': b['police_report_number'].strip()})
        try:
            getattr(i, method)()
        except Exception as e:
            return _err('تعذّر تنفيذ الإجراء: %s' % e, 400)
        return _ok({'state': i.state})

    @route(API + '/security/incident/<int:iid>/followup', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def incident_followup(self, iid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        i = env['security.incident.report'].sudo().browse(iid).exists()
        if not i:
            return _err('غير موجود', 404)
        b = _body() or {}
        vals = {'follow_up_required': bool(b.get('required'))}
        if 'follow_up_date' in i._fields and b.get('date'):
            vals['follow_up_date'] = b['date']
        if 'follow_up_notes' in i._fields:
            vals['follow_up_notes'] = (b.get('notes') or '').strip() or False
        i.write(vals)
        return _ok({'follow_up_required': i.follow_up_required})

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
