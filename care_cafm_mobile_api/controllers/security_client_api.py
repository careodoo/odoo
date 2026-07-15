# -*- coding: utf-8 -*-
"""Client-facing SECURITY endpoints — a full mirror of the security_management
module's client-relevant data, scoped to the client's facilities through the
care_cafm_security bridge (security.premise.cafm_facility_id → care.cafm.facility).

Everything is read with sudo() and hard-scoped to the caller's premises, so a
client only ever sees security data for their own sites."""
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _abs, API


def _sel(Model, field):
    """Resolve a selection field to {value: label} even when it is callable."""
    try:
        return dict(Model.fields_get([field])[field].get('selection') or [])
    except Exception:
        return {}


def _dt(v):
    return v and str(v) or None


class SecurityClientApi(Controller):

    # ---- scoping ----------------------------------------------------------
    def _facilities(self, env):
        if env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system'):
            return env['care.cafm.facility'].sudo().search([])
        p = env.user.partner_id
        pids = {p.id}
        if p.commercial_partner_id:
            pids.add(p.commercial_partner_id.id)
            pids.update(env['res.partner'].sudo().search(
                [('commercial_partner_id', '=', p.commercial_partner_id.id)]).ids)
        # CAFM client sub-users: bridge to the client company's partner
        if 'care.cafm.client' in env:
            clients = env['care.cafm.client'].sudo().search([('user_ids', 'in', [env.user.id])])
            for cp in clients.mapped('partner_id'):
                pids.add(cp.id)
                pids.update(env['res.partner'].sudo().search(
                    [('commercial_partner_id', '=', cp.id)]).ids)
        return env['care.cafm.facility'].sudo().search([('partner_id', 'in', list(pids))])

    def _scope(self, env):
        """Return (premise_ids, security_client_ids) for the caller, or (None, None)
        if the security module isn't installed."""
        if 'security.premise' not in env:
            return None, None
        facs = self._facilities(env)
        prem = env['security.premise'].sudo().search([('cafm_facility_id', 'in', facs.ids)]) if facs else env['security.premise'].sudo().browse()
        # managers with no bridged premises still see everything
        if not prem and (env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system')):
            prem = env['security.premise'].sudo().search([])
        return prem.ids, prem.mapped('client_id').ids

    def _guard(self, env):
        if 'security.premise' not in env:
            return _err('خدمة الأمن غير مفعّلة', 404)
        return None

    def _incident_model(self, env):
        """Two variants exist; prefer the one that actually holds records."""
        for m in ('security.incident.report', 'security.incidence.report'):
            if m in env:
                return env[m].sudo()
        return None

    # ---- summary ----------------------------------------------------------
    @route(API + '/client/security/summary', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def sec_summary(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'security.premise' not in env:
            return _ok({'available': False})
        pids, cids = self._scope(env)

        def cnt(model, dom):
            return env[model].sudo().search_count(dom) if model in env else 0

        inc_dom = [('premise_id', 'in', pids)]
        IncM = self._incident_model(env)
        inc_open = IncM.search_count(inc_dom + [('state', 'not in', ('closed', 'resolved', 'cancelled'))]) if IncM is not None else 0
        inc_total = IncM.search_count(inc_dom) if IncM is not None else 0
        return _ok({
            'available': True,
            'premises': len(pids or []),
            'incidents_open': inc_open,
            'incidents_total': inc_total,
            'inspections_open': cnt('security.inspection', [('premise_id', 'in', pids), ('state', 'not in', ('done', 'completed', 'closed', 'cancelled'))]),
            'gatepasses_active': cnt('security.gate.pass', [('premise_id', 'in', pids), ('state', 'in', ('approved', 'checked_in', 'active', 'confirmed'))]),
            'patrols_ongoing': cnt('security.patrol', [('premise_id', 'in', pids), ('state', 'in', ('in_progress', 'ongoing', 'started'))]),
            'guards_present': cnt('security.attendance', [('client_id', 'in', cids), ('state', 'in', ('checked_in', 'present', 'on_duty'))]),
            'keys_out': cnt('security.key', [('premise_id', 'in', pids), ('state', 'in', ('issued', 'out', 'borrowed'))]) if 'security.key' in env else 0,
        })

    # ---- incidents --------------------------------------------------------
    @route(API + '/client/security/incidents', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def sec_incidents(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        pids, cids = self._scope(env)
        M = self._incident_model(env)
        if M is None:
            return _ok([])
        st, sv, ty = _sel(M, 'state'), _sel(M, 'severity'), _sel(M, 'incident_type')
        recs = M.search([('premise_id', 'in', pids)], order='id desc', limit=200)
        return _ok([{
            'id': r.id, 'name': r.name, 'date': _dt(r.date),
            'premise': r.premise_id.name or None,
            'type': ty.get(getattr(r, 'incident_type', False), getattr(r, 'incident_type', '') or ''),
            'severity': sv.get(getattr(r, 'severity', False), getattr(r, 'severity', '') or ''),
            'severity_raw': getattr(r, 'severity', None),
            'description': (r.description or '')[:400],
            'state': r.state, 'state_label': st.get(r.state, r.state),
        } for r in recs])

    # ---- inspections ------------------------------------------------------
    @route(API + '/client/security/inspections', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def sec_inspections(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        pids, cids = self._scope(env)
        M = env['security.inspection'].sudo() if 'security.inspection' in env else None
        if M is None:
            return _ok([])
        st = _sel(M, 'state')
        recs = M.search([('premise_id', 'in', pids)], order='id desc', limit=200)
        return _ok([{
            'id': r.id, 'name': r.name,
            'premise': r.premise_id.name or None,
            'inspector': r.inspector_id.name if 'inspector_id' in r._fields and r.inspector_id else None,
            'date': _dt(getattr(r, 'inspection_date', False) or getattr(r, 'date', False)),
            'state': r.state, 'state_label': st.get(r.state, r.state),
            'issues': len(r.issue_ids) if 'issue_ids' in r._fields else 0,
        } for r in recs])

    # ---- patrols ----------------------------------------------------------
    @route(API + '/client/security/patrols', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def sec_patrols(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        pids, cids = self._scope(env)
        M = env['security.patrol'].sudo() if 'security.patrol' in env else None
        if M is None:
            return _ok([])
        st = _sel(M, 'state')
        recs = M.search([('premise_id', 'in', pids)], order='id desc', limit=150)
        return _ok([{
            'id': r.id, 'name': r.name,
            'route': r.route_id.name if 'route_id' in r._fields and r.route_id else None,
            'guard': r.guard_id.name if 'guard_id' in r._fields and r.guard_id else None,
            'premise': r.premise_id.name if 'premise_id' in r._fields and r.premise_id else None,
            'start': _dt(getattr(r, 'start_time', False)), 'end': _dt(getattr(r, 'end_time', False)),
            'state': r.state, 'state_label': st.get(r.state, r.state),
        } for r in recs])

    # ---- gate passes ------------------------------------------------------
    @route(API + '/client/security/gatepasses', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def sec_gatepasses(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        pids, cids = self._scope(env)
        M = env['security.gate.pass'].sudo() if 'security.gate.pass' in env else None
        if M is None:
            return _ok([])
        st = _sel(M, 'state')
        recs = M.search([('premise_id', 'in', pids)], order='id desc', limit=200)
        return _ok([{
            'id': r.id, 'name': r.name,
            'visitor': getattr(r, 'visitor_name', None) or (r.visitor_id.name if r.visitor_id else None),
            'company': getattr(r, 'visitor_company', None),
            'phone': getattr(r, 'visitor_phone', None),
            'purpose': (getattr(r, 'purpose', '') or '')[:200],
            'premise': r.premise_id.name if r.premise_id else None,
            'valid_from': _dt(getattr(r, 'valid_from', False)), 'valid_until': _dt(getattr(r, 'valid_until', False)),
            'persons': getattr(r, 'person_count', None),
            'vehicle': r.vehicle_id.display_name if 'vehicle_id' in r._fields and r.vehicle_id else None,
            'state': r.state, 'state_label': st.get(r.state, r.state),
        } for r in recs])

    # ---- visitor logs -----------------------------------------------------
    @route(API + '/client/security/visitors', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def sec_visitors(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        pids, cids = self._scope(env)
        M = env['security.visit.record'].sudo() if 'security.visit.record' in env else None
        if M is None:
            return _ok([])
        st = _sel(M, 'state')
        recs = M.search([('premise_id', 'in', pids)], order='id desc', limit=200)
        return _ok([{
            'id': r.id, 'name': r.name,
            'visitor': r.visitor_id.name if 'visitor_id' in r._fields and r.visitor_id else None,
            'check_in': _dt(getattr(r, 'check_in', False) or getattr(r, 'check_in_time', False)),
            'check_out': _dt(getattr(r, 'check_out', False) or getattr(r, 'check_out_time', False)),
            'premise': r.premise_id.name if 'premise_id' in r._fields and r.premise_id else None,
            'state': r.state if 'state' in r._fields else None,
            'state_label': st.get(getattr(r, 'state', False), getattr(r, 'state', None)),
        } for r in recs])

    # ---- guard attendance -------------------------------------------------
    @route(API + '/client/security/guards', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def sec_guards(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        pids, cids = self._scope(env)
        M = env['security.attendance'].sudo() if 'security.attendance' in env else None
        if M is None:
            return _ok([])
        st = _sel(M, 'state')
        recs = M.search([('client_id', 'in', cids)], order='id desc', limit=200)
        return _ok([{
            'id': r.id, 'name': r.name,
            'guard': r.guard_id.name if 'guard_id' in r._fields and r.guard_id else (
                r.employee_id.name if 'employee_id' in r._fields and r.employee_id else None),
            'date': _dt(getattr(r, 'date', False)),
            'check_in': _dt(getattr(r, 'check_in', False)), 'check_out': _dt(getattr(r, 'check_out', False)),
            'state': r.state, 'state_label': st.get(r.state, r.state),
        } for r in recs])

    # ---- key custody ------------------------------------------------------
    @route(API + '/client/security/keys', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def sec_keys(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        pids, cids = self._scope(env)
        M = env['security.key'].sudo() if 'security.key' in env else None
        if M is None:
            return _ok([])
        st = _sel(M, 'state')
        recs = M.search([('premise_id', 'in', pids)], order='id desc', limit=200)
        return _ok([{
            'id': r.id, 'name': r.display_name,
            'premise': r.premise_id.name if 'premise_id' in r._fields and r.premise_id else None,
            'holder': r.holder_id.name if 'holder_id' in r._fields and r.holder_id else None,
            'state': r.state if 'state' in r._fields else None,
            'state_label': st.get(getattr(r, 'state', False), getattr(r, 'state', None)),
        } for r in recs])
