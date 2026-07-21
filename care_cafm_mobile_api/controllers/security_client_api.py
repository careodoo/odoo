# -*- coding: utf-8 -*-
"""Client-facing SECURITY endpoints — a full mirror of the security_management
module's client-relevant data, scoped to the client's facilities through the
care_cafm_security bridge (security.premise.cafm_facility_id → care.cafm.facility).

Everything is read with sudo() and hard-scoped to the caller's premises, so a
client only ever sees security data for their own sites."""
from odoo import fields, _
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _body, _abs, API


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

    # ---- live security positioning (map of premises + coverage) -----------
    @route(API + '/client/security/positioning', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def sec_positioning(self, **kw):
        """One record per premise for the interactive positioning map: address
        (for geocoding), its patrol checkpoints with live status, guards on duty,
        open incidents, and an overall coverage/health score."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'security.premise' not in env:
            return _ok({'available': False})
        pids, cids = self._scope(env)
        prem = env['security.premise'].sudo().browse(pids).exists()
        Point = env['security.patrol.point'].sudo() if 'security.patrol.point' in env else None
        IncM = self._incident_model(env)
        Att = env['security.attendance'].sudo() if 'security.attendance' in env else None
        # guards currently on duty (client-level: checked in, not out)
        on_duty = {}
        if Att is not None:
            for a in Att.search([('client_id', 'in', cids),
                                 ('state', 'in', ('checked_in', 'present', 'on_duty')),
                                 ('check_out', '=', False)], limit=300):
                on_duty.setdefault(a.client_id.id, []).append({
                    'name': (a.security_employee_id.name or '—'),
                    'since': _dt(a.check_in)})
        out = []
        for p in prem:
            pts = Point.search([('premise_id', '=', p.id)]) if Point is not None else []
            st = _sel(Point, 'last_check_status') if Point is not None else {}
            checkpoints = [{
                'id': c.id, 'name': c.name,
                'status': c.last_check_status, 'status_label': st.get(c.last_check_status, c.last_check_status or ''),
                'last_check': _dt(c.last_check_time), 'next_check': _dt(c.next_check_time),
                'overdue': c.last_check_status in ('late', 'missed'),
            } for c in pts]
            overdue = sum(1 for c in checkpoints if c['overdue'])
            inc_open = (IncM.search_count([('premise_id', '=', p.id),
                        ('state', 'not in', ('closed', 'resolved', 'cancelled'))]) if IncM is not None else 0)
            total = len(checkpoints) or 1
            coverage = round((total - overdue) * 100.0 / total)
            # health: green (>=85 & no incidents) / amber / red
            health = 'good' if (coverage >= 85 and inc_open == 0) else ('warn' if coverage >= 60 and inc_open <= 1 else 'risk')
            guards = on_duty.get(p.client_id.id, []) if 'client_id' in p._fields and p.client_id else []
            out.append({
                'id': p.id, 'name': p.name, 'address': p.address or None,
                'client': p.client_id.name if 'client_id' in p._fields and p.client_id else None,
                'checkpoints': checkpoints, 'guards_on_duty': guards,
                'stats': {'checkpoints': len(checkpoints), 'overdue': overdue,
                          'incidents_open': inc_open, 'guards': len(guards), 'coverage': coverage},
                'health': health,
            })
        return _ok({'available': True, 'premises': out})

    # ---- issue a gate pass (client-issued "permit") -----------------------
    @route(API + '/client/security/options', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def sec_options(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        pids, cids = self._scope(env)
        clients = env['security.client'].sudo().browse(cids).exists()
        prem = env['security.premise'].sudo().browse(pids).exists()
        routes = []
        if 'security.patrol.route' in env:
            routes = [{'id': r.id, 'name': r.name, 'premise_id': r.premise_id.id}
                      for r in env['security.patrol.route'].sudo().search([('premise_id', 'in', pids)])]
        return _ok({
            'clients': [{'id': c.id, 'name': c.name} for c in clients],
            'premises': [{'id': p.id, 'name': p.name,
                          'client_id': p.client_id.id if 'client_id' in p._fields and p.client_id else None}
                         for p in prem],
            'routes': routes,
        })

    @route(API + '/client/security/gatepass/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def sec_gatepass_create(self, **kw):
        """Client issues a gate pass (personal or vehicle) — starts as draft for
        the security team to approve."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        if 'security.gate.pass' not in env:
            return _err('غير متاح', 404)
        pids, cids = self._scope(env)
        b = _body()
        cid = int(b['client_id']) if b.get('client_id') else (cids[0] if cids else None)
        if not cid or cid not in cids:
            return _err('العميل الأمني غير محدد', 422)
        if not (b.get('purpose') or '').strip():
            return _err('الغرض مطلوب', 422)
        if not b.get('start_date') or not b.get('end_date'):
            return _err('تاريخ البداية والنهاية مطلوبان', 422)
        GP = env['security.gate.pass'].sudo()
        vals = {
            'client_id': cid,
            'start_date': fields.Date.to_date(b['start_date']),
            'end_date': fields.Date.to_date(b['end_date']),
            'purpose': b['purpose'].strip(),
            'pass_type': b.get('pass_type') or 'personal',
        }
        if b.get('premise_id') and 'premise_id' in GP._fields and int(b['premise_id']) in pids:
            vals['premise_id'] = int(b['premise_id'])
        gp = GP.create(vals)
        # personal pass → add the visitor person(s)
        if vals['pass_type'] == 'personal' and 'security.gate.pass.person' in env:
            persons = b.get('persons') or []
            if not persons and b.get('person_name'):
                persons = [{'name': b.get('person_name'), 'id_number': b.get('id_number'),
                            'phone': b.get('phone'), 'company': b.get('company')}]
            for pr in persons:
                if not pr.get('name'):
                    continue
                env['security.gate.pass.person'].sudo().create({
                    'gate_pass_id': gp.id, 'name': pr['name'],
                    'id_number': pr.get('id_number') or '—',
                    'phone': pr.get('phone') or None, 'company': pr.get('company') or None,
                })
        st = _sel(GP, 'state')
        return _ok({'id': gp.id, 'name': gp.name, 'state': gp.state,
                    'state_label': st.get(gp.state, gp.state)})

    @route('/cafm/security/gatepasses/export', type='http', auth='public', methods=['GET'], csrf=False)
    def sec_gatepasses_export(self, **kw):
        from .client_api import _xlsx_response, _report_env
        env = _report_env()
        if not env:
            return request.redirect('/web/login')
        pids, cids = self._scope(env)
        M = env['security.gate.pass'].sudo()
        st = _sel(M, 'state')
        dom = [('premise_id', 'in', pids)] if 'premise_id' in M._fields else [('client_id', 'in', cids)]
        recs = M.search(dom, order='id desc', limit=5000)
        columns = [_('#'), _('المرجع'), _('النوع'), _('من'), _('إلى'), _('الغرض'), _('العدد'), _('الحالة')]
        pt = _sel(M, 'pass_type')
        rows = []
        for i, r in enumerate(recs, 1):
            rows.append([i, r.name, pt.get(r.pass_type, r.pass_type or ''),
                         _dt(r.start_date) or '', _dt(r.end_date) or '',
                         (r.purpose or '')[:80], r.person_count if 'person_count' in r._fields else '',
                         st.get(r.state, r.state or '')])
        meta = [(_('العميل'), env.user.partner_id.commercial_partner_id.name), (_('عدد التصاريح'), len(recs))]
        return _xlsx_response(_('تصاريح الدخول'), columns, rows, 'gate-passes.xlsx', meta)

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

    @route(API + '/client/security/keyhubs', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def sec_keyhubs(self, **kw):
        """Key hubs → the keys in each → their latest in/out log. The physical
        key-custody board from security_management, scoped to the client."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        pids, cids = self._scope(env)
        Hub = env['security.key.hub'].sudo() if 'security.key.hub' in env else None
        if Hub is None:
            return _ok([])
        kst = _sel(env['security.key'], 'state') if 'security.key' in env else {}
        hubs = Hub.search([('premise_id', 'in', pids)], limit=60)
        out = []
        for h in hubs:
            keys = []
            for k in h.key_ids:
                logs = k.log_ids.sorted('timestamp', reverse=True)[:5] if 'log_ids' in k._fields else k.env['security.key.log'].browse()
                keys.append({
                    'id': k.id, 'name': k.name,
                    'key_number': k.key_number if 'key_number' in k._fields else None,
                    'door': k.door_number if 'door_number' in k._fields else None,
                    'nfc': (k.nfc_uid or None) if 'nfc_uid' in k._fields else None,
                    'state': k.state, 'state_label': kst.get(k.state, k.state),
                    'holder': k.current_holder_id.name if getattr(k, 'current_holder_id', False) else None,
                    'out_since': str(getattr(k, 'check_out_time', '') or '')[:16] or None,
                    'logs': [{
                        'op': l.operation,
                        'by': l.security_employee_id.name if getattr(l, 'security_employee_id', False) else None,
                        'at': str(l.timestamp or '')[:16],
                    } for l in logs],
                })
            out.append({
                'id': h.id, 'name': h.name, 'code': h.code, 'location': h.location,
                'responsible': h.responsible_id.name if h.responsible_id else None,
                'key_count': len(h.key_ids),
                'out_count': sum(1 for k in h.key_ids if k.state == 'checked_out'),
                'keys': keys,
            })
        return _ok(out)

    @route(API + '/client/security/cashier', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def sec_cashier(self, **kw):
        """Gate-cashier board: today's takings, per-cashier breakdown, and the
        latest receipts — all scoped to this client's gate-pass payments."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        pids, cids = self._scope(env)
        Pay = env['security.gate.pass.payment'].sudo() if 'security.gate.pass.payment' in env else None
        if Pay is None:
            return _ok({'available': False})
        meth = _sel(Pay, 'payment_method')
        stt = _sel(Pay, 'state')
        today = fields.Date.today()
        dom = [('client_id', 'in', cids)] if cids else []
        payments = Pay.search(dom, order='payment_date desc, id desc', limit=120)
        today_pays = payments.filtered(lambda p: p.payment_date == today)
        cashiers = {}
        for p in today_pays:
            c = p.cashier_id
            key = c.id or 0
            cashiers.setdefault(key, {
                'name': (c.name if c else None) or '—',
                'gate': (c.gate_id.name if c and c.gate_id else None),
                'count': 0, 'amount': 0.0})
            cashiers[key]['count'] += 1
            cashiers[key]['amount'] = round(cashiers[key]['amount'] + (p.amount or 0.0), 3)
        return _ok({
            'available': True,
            'currency': (payments[:1].currency_id.name if payments else None) or 'KWD',
            'today_total': round(sum(today_pays.mapped('amount')), 3),
            'today_count': len(today_pays),
            'cashiers': sorted(cashiers.values(), key=lambda x: -x['amount']),
            'recent': [{
                'id': p.id, 'name': p.name, 'amount': round(p.amount or 0.0, 3),
                'method': meth.get(p.payment_method, p.payment_method),
                'visitor': p.visitor_name or (p.visitor_id.name if p.visitor_id else None),
                'company': p.visitor_company or None,
                'date': str(p.payment_date or ''),
                'state': stt.get(p.state, p.state),
                'cashier': p.cashier_id.name if p.cashier_id else None,
            } for p in payments[:50]],
        })
