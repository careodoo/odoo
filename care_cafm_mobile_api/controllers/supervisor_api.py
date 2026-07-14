# -*- coding: utf-8 -*-
"""Supervisor endpoints: see the team's load, the assignable backlog, and assign
work orders to employees from the phone."""
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _body, API, _wo_dict


def _emp_dict(e, wo_model):
    mine = wo_model.search([('employee_id', '=', e.id)])
    return {
        'id': e.id, 'name': e.name,
        'job_title': e.job_title or None,
        'open': len(mine.filtered(lambda w: w.state not in ('done', 'verified', 'cancelled'))),
        'overdue': len(mine.filtered('is_overdue')),
        'done': len(mine.filtered(lambda w: w.state in ('done', 'verified'))),
    }


class SupervisorApi(Controller):

    @route(API + '/stats', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def stats(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        WO = env['care.cafm.workorder']
        all_wo = WO.search([])
        open_wo = all_wo.filtered(lambda w: w.state not in ('done', 'verified', 'cancelled'))
        by_service = {}
        for w in open_wo:
            by_service[w.service_type or 'other'] = by_service.get(w.service_type or 'other', 0) + 1
        return _ok({
            'open': len(open_wo),
            'overdue': len(all_wo.filtered('is_overdue')),
            'unassigned': len(open_wo.filtered(lambda w: not w.employee_id)),
            'done': len(all_wo.filtered(lambda w: w.state in ('done', 'verified'))),
            'by_service': by_service,
            'team_size': env['hr.employee'].search_count([('user_id', '!=', False)]),
        })

    @route(API + '/team', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def team(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        WO = env['care.cafm.workorder']
        emps = env['hr.employee'].search([('user_id', '!=', False)])
        # sort busiest-first so a supervisor sees pressure points at the top
        data = sorted([_emp_dict(e, WO) for e in emps], key=lambda d: -d['open'])
        return _ok(data)

    @route(API + '/employees', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def employees(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        # sudo — portal/client users have no direct ACL on hr.employee
        emps = env['hr.employee'].sudo().search([], limit=1000)
        return _ok([{'id': e.id, 'name': e.name, 'job_title': e.job_title or None} for e in emps])

    @route(API + '/workorders/assignable', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def assignable(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        # unassigned or still-open work — the backlog a supervisor distributes
        dom = ['|', ('employee_id', '=', False),
               ('state', 'in', ('new', 'assigned'))]
        wos = env['care.cafm.workorder'].search(dom, limit=200)
        return _ok([_wo_dict(w) for w in wos])

    @route(API + '/workorders/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def create_task(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        _cp = env.user.partner_id.commercial_partner_id or env.user.partner_id
        if not (env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system')
                or env.user.has_group('security_management.group_security_manager')
                or (_cp and _cp.sudo().cafm_can_add_workers)):
            return _err('غير مسموح بإنشاء المهام', 403)
        b = _body()
        emp = env['hr.employee'].sudo().browse(int(b['employee_id'])).exists() if b.get('employee_id') else None
        if not emp:
            return _err('الموظف مطلوب', 422)
        WO = env['care.cafm.workorder'].sudo()
        # facility/service: from the worker's latest work order, else first available
        ref = WO.search([('employee_id', '=', emp.id)], limit=1)
        facility = env['care.cafm.facility'].sudo().browse(int(b['facility_id'])) if b.get('facility_id') \
            else (ref.facility_id or env['care.cafm.facility'].sudo().search([], limit=1))
        service = env['care.cafm.service'].sudo().browse(int(b['service_id'])) if b.get('service_id') \
            else (ref.service_id or env['care.cafm.service'].sudo().search([], limit=1))
        location = env['care.cafm.location'].sudo().browse(int(b['location_id'])) if b.get('location_id') else ref.location_id
        vals = {
            'title': b.get('title') or 'مهمة جديدة',
            'facility_id': facility.id, 'service_id': service.id,
            'employee_id': emp.id, 'state': 'assigned',
            'expected_minutes': int(b.get('expected_minutes') or 60),
            'description': b.get('description') or None,
            'instructions': b.get('instructions') or None,
            'supervisor_id': env.user.id,
        }
        if location:
            vals['location_id'] = location.id
        # proof requirements (default: presence + photo)
        for f in ('proof_presence', 'proof_photo', 'proof_video'):
            if f in b:
                vals[f] = bool(b.get(f))
        if b.get('priority') is not None:
            vals['priority'] = str(b.get('priority'))
        w = WO.create(vals)
        if emp.user_id:
            env['care.cafm.notification'].sudo().push(
                emp.user_id, 'مهمة جديدة', 'أُسندت إليك: %s' % w.title, ntype='task',
                author=env.user, action_url='/workorder/%s' % w.id)
        return _ok(_wo_dict(w))

    @route(API + '/workorders/<int:wid>/assign', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def assign(self, wid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        emp_id = _body().get('employee_id')
        if not emp_id:
            return _err('employee_id مطلوب', 422)
        # read with sudo — client/portal users have no ACL on these models
        w = env['care.cafm.workorder'].sudo().browse(wid).exists()
        if not w:
            return _err('غير موجود', 404)
        emp = env['hr.employee'].sudo().browse(int(emp_id)).exists()
        if not emp:
            return _err('الموظف غير موجود', 404)
        w.sudo().employee_id = emp.id
        if w.state == 'new':
            w.sudo().state = 'assigned'
        # notify the newly-assigned worker
        if emp.user_id:
            env['care.cafm.notification'].sudo().push(
                emp.user_id, 'مهمة جديدة', 'أُسندت إليك: %s' % w.title, ntype='task',
                author=env.user, action_url='/workorder/%s' % w.id)
        return _ok(_wo_dict(w))
