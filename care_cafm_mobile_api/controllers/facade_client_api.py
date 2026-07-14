# -*- coding: utf-8 -*-
"""Client-facing FACADE-CLEANING endpoints — surfaces the care_cafm_facade
module's elevation zones (frequency/compliance) and height-work permits (with
wind-lockout safety), hard-scoped to the caller's facilities. Read-only:
clients get full visibility into façade cleaning compliance and site safety."""
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, API


def _sel(Model, field):
    try:
        return dict(Model.fields_get([field])[field].get('selection') or [])
    except Exception:
        return {}


def _d(v):
    return v and str(v) or None


class FacadeClientApi(Controller):

    def _facilities(self, env):
        if env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system'):
            return env['care.cafm.facility'].sudo().search([])
        p = env.user.partner_id
        pids = {p.id}
        if p.commercial_partner_id:
            pids.add(p.commercial_partner_id.id)
            pids.update(env['res.partner'].sudo().search(
                [('commercial_partner_id', '=', p.commercial_partner_id.id)]).ids)
        return env['care.cafm.facility'].sudo().search([('partner_id', 'in', list(pids))])

    def _fac_ids(self, env):
        facs = self._facilities(env)
        fid = request.httprequest.args.get('facility_id')
        if fid and fid.isdigit() and int(fid) in facs.ids:
            return [int(fid)]
        return facs.ids

    def _guard(self, env):
        if 'care.cafm.facade.zone' not in env:
            return _err('خدمة غسيل الواجهات غير مفعّلة', 404)
        return None

    # ---- summary ----------------------------------------------------------
    @route(API + '/client/facade/summary', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def facade_summary(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.cafm.facade.zone' not in env:
            return _ok({'available': False})
        fids = self._fac_ids(env)
        Zone = env['care.cafm.facade.zone'].sudo()
        Permit = env['care.cafm.facade.permit'].sudo()
        zones = Zone.search([('facility_id', 'in', fids)])
        permits = Permit.search([('facility_id', 'in', fids)])
        active = permits.filtered(lambda p: p.state in ('approved', 'active'))
        return _ok({
            'available': True,
            'zones': len(zones),
            'zones_due': len(zones.filtered('is_due')),
            'permits_active': len(active),
            'permits_total': len(permits),
            'wind_unsafe': len(active.filtered(lambda p: not p.is_safe)),
        })

    # ---- elevation zones --------------------------------------------------
    @route(API + '/client/facade/zones', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def facade_zones(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        M = env['care.cafm.facade.zone'].sudo()
        mth, fr = _sel(M, 'method'), _sel(M, 'frequency')
        recs = M.search([('facility_id', 'in', self._fac_ids(env))], order='facility_id, name')
        return _ok([{
            'id': z.id, 'name': z.name, 'facility': z.facility_id.name or None,
            'method': mth.get(z.method, z.method or ''), 'method_raw': z.method,
            'frequency': fr.get(z.frequency, z.frequency or ''),
            'last_cleaned': _d(z.last_cleaned), 'next_due': _d(z.next_due), 'is_due': z.is_due,
        } for z in recs])

    # ---- height-work permits ----------------------------------------------
    @route(API + '/client/facade/permits', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def facade_permits(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        M = env['care.cafm.facade.permit'].sudo()
        st, mth = _sel(M, 'state'), _sel(M, 'method')
        recs = M.search([('facility_id', 'in', self._fac_ids(env))], order='date desc, id desc', limit=200)
        return _ok([{
            'id': p.id, 'name': p.name, 'facility': p.facility_id.name or None,
            'zone': p.zone_id.name or None,
            'method': mth.get(p.method, p.method or ''), 'date': _d(p.date),
            'valid_hours': p.valid_hours,
            'wind_speed': p.wind_speed, 'wind_limit': p.wind_limit, 'is_safe': p.is_safe,
            'risk_assessed': p.risk_assessed, 'equipment_checked': p.equipment_checked,
            'supervisor': p.supervisor_id.name or None,
            'workers': p.worker_ids.mapped('name'),
            'state': p.state, 'state_label': st.get(p.state, p.state or ''),
        } for p in recs])
