# -*- coding: utf-8 -*-
"""Client-facing FACADE-CLEANING endpoints — surfaces the care_cafm_facade
module's elevation zones (frequency/compliance) and height-work permits (with
wind-lockout safety), hard-scoped to the caller's facilities. Read-only:
clients get full visibility into façade cleaning compliance and site safety."""
from odoo import fields, _
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _body, API


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
        # CAFM client sub-users: bridge to the client company's partner
        if 'care.cafm.client' in env:
            clients = env['care.cafm.client'].sudo().search([('user_ids', 'in', [env.user.id])])
            for cp in clients.mapped('partner_id'):
                pids.add(cp.id)
                pids.update(env['res.partner'].sudo().search(
                    [('commercial_partner_id', '=', cp.id)]).ids)
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

    # ---- options for the "issue permit" form ------------------------------
    @route(API + '/client/facade/options', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def facade_options(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        facs = self._facilities(env)
        zones = env['care.cafm.facade.zone'].sudo().search([('facility_id', 'in', facs.ids)])
        # workers on the client's sites (facade crews)
        try:
            from .client_api import ClientApi
            emps = ClientApi()._client_workers(env, facs)
        except Exception:
            emps = env['hr.employee'].sudo().browse()
        mth = _sel(env['care.cafm.facade.zone'].sudo(), 'method')
        return _ok({
            'facilities': [{'id': f.id, 'name': f.name} for f in facs],
            'zones': [{'id': z.id, 'name': z.name, 'facility_id': z.facility_id.id,
                       'method': z.method, 'method_label': mth.get(z.method, z.method or '')} for z in zones],
            'methods': [{'v': k, 'l': v} for k, v in mth.items()],
            'workers': [{'id': e.id, 'name': e.name} for e in emps],
            'wind_limit_default': 40.0,
        })

    @route(API + '/client/facade/permit/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def facade_permit_create(self, **kw):
        """Client issues a height-work permit (submitted for safety approval)."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        b = _body()
        fid = int(b['facility_id']) if b.get('facility_id') else (self._facilities(env)[:1].id or None)
        if not fid or fid not in self._facilities(env).ids:
            return _err('المرفق مطلوب', 422)
        vals = {
            'facility_id': fid,
            'zone_id': int(b['zone_id']) if b.get('zone_id') else False,
            'valid_hours': float(b.get('valid_hours') or 6.0),
            'wind_speed': float(b.get('wind_speed') or 0.0),
            'wind_limit': float(b.get('wind_limit') or 40.0),
            'risk_assessed': bool(b.get('risk_assessed')),
            'equipment_checked': bool(b.get('equipment_checked')),
        }
        if b.get('date'):
            try:
                vals['date'] = fields.Date.to_date(b['date'])
            except Exception:
                pass
        if b.get('worker_ids'):
            ids = [int(x) for x in b['worker_ids'] if str(x).isdigit()]
            if ids:
                vals['worker_ids'] = [(6, 0, ids)]
        p = env['care.cafm.facade.permit'].sudo().create(vals)
        # move to submitted when the safety pre-reqs are ticked
        if vals['risk_assessed'] and vals['equipment_checked']:
            try:
                p.action_submit()
            except Exception:
                pass
        st = _sel(env['care.cafm.facade.permit'].sudo(), 'state')
        return _ok({'id': p.id, 'name': p.name, 'state': p.state,
                    'state_label': st.get(p.state, p.state), 'is_safe': p.is_safe})

    @route('/cafm/facade/permits/export', type='http', auth='user', methods=['GET'], csrf=False)
    def facade_permits_export(self, **kw):
        from .client_api import _xlsx_response
        env = request.env
        M = env['care.cafm.facade.permit'].sudo()
        st, mth = _sel(M, 'state'), _sel(M, 'method')
        recs = M.search([('facility_id', 'in', self._fac_ids(env))], order='date desc, id desc', limit=5000)
        columns = [_('#'), _('المرجع'), _('التاريخ'), _('المرفق'), _('الواجهة'), _('الطريقة'),
                   _('الرياح'), _('الحد الآمن'), _('آمن؟'), _('المشرف'), _('الحالة')]
        rows = []
        for i, p in enumerate(recs, 1):
            rows.append([i, p.name, _d(p.date) or '', p.facility_id.name or '', p.zone_id.name or '',
                         mth.get(p.method, p.method or ''), p.wind_speed, p.wind_limit,
                         _('نعم') if p.is_safe else _('لا'), p.supervisor_id.name or '',
                         st.get(p.state, p.state or '')])
        meta = [(_('العميل'), env.user.partner_id.commercial_partner_id.name),
                (_('عدد التصاريح'), len(recs))]
        return _xlsx_response(_('تصاريح العمل على الارتفاع'), columns, rows, 'facade-permits.xlsx', meta)
