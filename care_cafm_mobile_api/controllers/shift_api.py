# -*- coding: utf-8 -*-
"""Geofenced shift open/close + availability, and worker appraisal scoring."""
from odoo.http import Controller, route

from .api import _auth, _ok, _err, _body, API


def _notify_supervisors(env, title, body):
    """Notify the recipients configured in settings, or fall back to the
    erp-manager + security-manager groups."""
    users = env.company.sudo().cafm_shift_notify_user_ids
    if not users:
        gids = [env.ref('base.group_erp_manager').id]
        smg = env.ref('security_management.group_security_manager', raise_if_not_found=False)
        if smg:
            gids.append(smg.id)
        users = env['res.users'].sudo().search([('groups_id', 'in', gids), ('active', '=', True)])
    if users:
        env['care.cafm.notification'].sudo().push(users, title, body, ntype='info')


def _shift_dict(s):
    return {'id': s.id, 'name': s.name, 'facility': s.facility_id.name or None,
            'check_in': s.check_in or None, 'check_out': s.check_out or None,
            'in_distance': s.in_distance, 'state': s.state,
            'duration_hours': round(s.duration_hours, 2)}


class ShiftApi(Controller):

    @route(API + '/shift/current', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def current(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        emp = env.user.employee_id
        if not emp:
            return _ok({'open': None, 'available': False})
        s = env['care.cafm.shift'].sudo().search(
            [('employee_id', '=', emp.id), ('state', '=', 'open')], limit=1)
        return _ok({'open': _shift_dict(s) if s else None, 'available': bool(s)})

    @route(API + '/shift/open', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def open(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        emp = env.user.employee_id
        if not emp:
            return _err('لا يوجد ملف موظف لهذا المستخدم', 422)
        b = _body()
        try:
            lat, lng = float(b['lat']), float(b['lng'])
        except Exception:
            return _err('الموقع (lat/lng) مطلوب', 422)
        try:
            s = env['care.cafm.shift'].sudo().open_for(emp, lat, lng)
        except Exception as e:
            return _err(str(e), 400)
        _notify_supervisors(env, '🟢 فتح وردية',
                            '%s فتح ورديته في %s.' % (emp.name, s.facility_id.name or ''))
        return _ok(_shift_dict(s))

    @route(API + '/shift/close', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def close(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        emp = env.user.employee_id
        s = env['care.cafm.shift'].sudo().search(
            [('employee_id', '=', emp.id), ('state', '=', 'open')], limit=1) if emp else None
        if not s:
            return _err('لا توجد وردية مفتوحة', 404)
        b = _body()
        s.close_shift(b.get('lat'), b.get('lng'))
        _notify_supervisors(env, '🔴 إغلاق وردية',
                            '%s أغلق ورديته (%.1f ساعة).' % (emp.name, s.duration_hours))
        return _ok(_shift_dict(s))

    @route(API + '/shift/active', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def active(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        shifts = env['care.cafm.shift'].sudo().search([('state', '=', 'open')])
        return _ok([{'employee': s.employee_id.name, 'facility': s.facility_id.name or None,
                     'since': s.check_in, 'distance': s.in_distance} for s in shifts])

    # ---- appraisal -----------------------------------------------------------
    def _score(self, env, emp):
        WO = env['care.cafm.workorder'].sudo()
        wos = WO.search([('employee_id', '=', emp.id)])
        total = len(wos)
        done = wos.filtered(lambda w: w.state in ('done', 'verified'))
        verified = wos.filtered(lambda w: w.state == 'verified')
        # 4 axes → 0..100
        volume = min(100.0, len(done) * 10.0)
        completion = (100.0 * len(done) / total) if total else 0.0
        # speed: expected vs actual on done WOs that have both
        ratios = []
        for w in done:
            if w.duration_minutes and w.expected_minutes:
                ratios.append(min(100.0, 100.0 * w.expected_minutes / w.duration_minutes))
        speed = (sum(ratios) / len(ratios)) if ratios else 100.0
        # quality: approved (verified) share of done
        quality = (100.0 * len(verified) / len(done)) if done else 0.0
        overall = round(0.30 * volume + 0.25 * completion + 0.20 * speed + 0.25 * quality, 1)
        rating = ('ممتاز' if overall >= 85 else 'جيد جداً' if overall >= 70
                  else 'جيد' if overall >= 50 else 'ضعيف')
        return {
            'employee': emp.name, 'job_title': emp.job_title or None,
            'overall': overall, 'rating': rating,
            'axes': {'volume': round(volume), 'completion': round(completion),
                     'speed': round(speed), 'quality': round(quality)},
            'total': total, 'done': len(done), 'verified': len(verified),
        }

    @route(API + '/appraisal/me', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def appraisal_me(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        emp = env.user.employee_id
        if not emp:
            return _err('لا يوجد ملف موظف', 404)
        return _ok(self._score(env, emp))

    @route(API + '/appraisal/team', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def appraisal_team(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        emps = env['hr.employee'].sudo().search([('user_id', '!=', False)])
        data = [self._score(env, e) for e in emps]
        data.sort(key=lambda d: -d['overall'])
        return _ok(data)
