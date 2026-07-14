# -*- coding: utf-8 -*-
"""Company-wide admin dashboard for CARE — everything across all clients."""
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _body, API, _wo_dict, MobileApi
from odoo.http import request


class AdminApi(Controller):

    # ---- test-only user switcher (admin) -------------------------------------
    @route(API + '/admin/users', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def users(self, **kw):
        env = _auth()
        if not env or not env.user.has_group('base.group_system'):
            return _err('للأدمن فقط', 403)
        users = env['res.users'].sudo().search(
            [('active', '=', True), ('login', 'not in', ('__system__', 'public'))], order='share, name')
        return _ok([{'login': u.login, 'name': u.name,
                     'kind': ('عميل' if u.share else ('أدمن' if u.has_group('base.group_system') else 'موظف'))}
                    for u in users if u.login])

    @route(API + '/admin/impersonate', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def impersonate(self, **kw):
        env = _auth()
        if not env or not env.user.has_group('base.group_system'):
            return _err('للأدمن فقط', 403)
        login = (_body().get('login') or '').strip()
        user = env['res.users'].sudo().search([('login', '=', login), ('active', '=', True)], limit=1)
        if not user:
            return _err('مستخدم غير موجود', 404)
        tok = env['care.cafm.mobile.token'].sudo().issue(user, 'impersonation')
        payload = MobileApi()._me_payload(request.env(user=user.id))
        payload['impersonating'] = True
        return _ok(payload, token=tok.token)

    @route(API + '/admin/dashboard', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def dashboard(self, **kw):
        env = _auth()
        if not env or not env.user.has_group('base.group_system'):
            return _err('غير مصرّح', 403)
        env = env(su=True)  # company-wide read
        WO = env['care.cafm.workorder']
        Fac = env['care.cafm.facility']
        all_wo = WO.search([])
        open_wo = all_wo.filtered(lambda w: w.state not in ('done', 'verified', 'cancelled'))
        done_wo = all_wo.filtered(lambda w: w.state in ('done', 'verified'))

        # by state
        state_lbl = dict(WO._fields['state'].selection)
        by_state = {}
        for st, lbl in state_lbl.items():
            by_state[lbl] = len(all_wo.filtered(lambda w: w.state == st))

        # by service
        svc_lbl = dict(env['care.cafm.service']._fields['service_type'].selection)
        by_service = {}
        for w in all_wo:
            key = svc_lbl.get(w.service_type, w.service_type or 'أخرى')
            d = by_service.setdefault(key, {'total': 0, 'open': 0})
            d['total'] += 1
            if w in open_wo:
                d['open'] += 1

        # SLA: done within deadline
        done_dl = done_wo.filtered(lambda w: w.done_datetime and w.deadline)
        in_sla = done_dl.filtered(lambda w: w.done_datetime <= w.deadline)
        sla = round(100.0 * len(in_sla) / len(done_dl), 1) if done_dl else 100.0

        # top facilities by open work
        facs = Fac.search([])
        top = sorted(
            [{'name': f.name,
              'open': len(open_wo.filtered(lambda w: w.facility_id == f)),
              'overdue': len(all_wo.filtered(lambda w: w.facility_id == f and w.is_overdue))}
             for f in facs],
            key=lambda d: -d['open'])[:6]

        clients = env['res.partner'].search_count([('cafm_facility_ids', '!=', False)])
        return _ok({
            'company': env.company.name,
            'kpis': {
                'clients': clients,
                'facilities': len(facs),
                'buildings': sum(len(f.building_ids) for f in facs),
                'locations': env['care.cafm.location'].search_count([]),
                'services': env['care.cafm.service'].search_count([]),
                'teams': env['care.cafm.team'].search_count([]),
                'employees': env['hr.employee'].search_count([('user_id', '!=', False)]),
                'total': len(all_wo),
                'open': len(open_wo),
                'overdue': len(all_wo.filtered('is_overdue')),
                'done': len(done_wo),
                'unassigned': len(open_wo.filtered(lambda w: not w.employee_id)),
                'sla': sla,
                'notifications': env['care.cafm.notification'].search_count([]),
            },
            'by_state': by_state,
            'by_service': by_service,
            'top_facilities': top,
            'recent': [_wo_dict(w) for w in all_wo[:12]],
        })
