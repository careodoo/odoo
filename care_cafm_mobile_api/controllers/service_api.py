# -*- coding: utf-8 -*-
"""Per-service data endpoints so each worker face (cleaning / agriculture /
facade) has its own real screens, not a generic list."""
from odoo.http import Controller, route

from .api import _auth, _ok, _err, API


class ServiceApi(Controller):

    @route(API + '/service/cleaning/audits', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def audits(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        A = env['care.cafm.clean.audit'].sudo()
        recs = A.search([], order='audit_date desc', limit=120)
        rate_lbl = dict(A._fields['rating'].selection)
        st_lbl = dict(A._fields['state'].selection)
        ack_lbl = dict(A._fields['client_ack'].selection)
        return _ok([{
            'id': a.id, 'name': a.name, 'facility': a.facility_id.name or None,
            'location': a.location_id.name or None,
            'score': round(a.score, 1), 'rating': a.rating,
            'rating_label': rate_lbl.get(a.rating) if a.rating else None,
            'fail_count': a.fail_count, 'state': a.state,
            'state_label': st_lbl.get(a.state, a.state),
            'items': len(a.line_ids),
            'auditor': a.auditor_id.name or None,
            'template': a.template_id.name or None,
            'client_ack': a.client_ack,
            'client_ack_label': ack_lbl.get(a.client_ack) if a.client_ack else None,
            'date': a.audit_date or None,
        } for a in recs])

    @route(API + '/service/cleaning/audit/<int:aid>', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def audit_detail(self, aid, **kw):
        """One audit in full: its checklist item by item, so a worker sees exactly
        what passed, what failed and the note behind each failure."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        a = env['care.cafm.clean.audit'].sudo().browse(aid).exists()
        if not a:
            return _err('غير موجود', 404)
        A = env['care.cafm.clean.audit']
        L = env['care.cafm.clean.audit.line']
        res_lbl = dict(L._fields['result'].selection)
        return _ok({
            'id': a.id, 'name': a.name,
            'facility': a.facility_id.name or None, 'location': a.location_id.name or None,
            'template': a.template_id.name or None,
            'auditor': a.auditor_id.name or None,
            'date': a.audit_date or None,
            'score': round(a.score, 1), 'rating': a.rating,
            'rating_label': dict(A._fields['rating'].selection).get(a.rating) if a.rating else None,
            'fail_count': a.fail_count,
            'state': a.state, 'state_label': dict(A._fields['state'].selection).get(a.state, a.state),
            'client_ack': a.client_ack,
            'client_ack_label': dict(A._fields['client_ack'].selection).get(a.client_ack) if a.client_ack else None,
            'client_ack_comment': a.client_ack_comment or None,
            'lines': [{
                'id': l.id, 'name': l.name, 'weight': l.weight,
                'result': l.result, 'result_label': res_lbl.get(l.result, l.result),
                'note': l.note or None,
            } for l in a.line_ids],
        })

    @route(API + '/service/agri/zones', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def zones(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        recs = env['care.cafm.agri.zone'].sudo().search([], order='name', limit=80)
        return _ok([{
            'id': z.id, 'name': z.name, 'facility': z.facility_id.name or None,
            'method': z.method, 'frequency': z.frequency,
            'weather_based': z.weather_based, 'is_due': z.is_due,
            'water_m3': z.water_m3, 'next_run': z.next_run or None,
        } for z in recs])

    @route(API + '/service/facade/permits', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def permits(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        recs = env['care.cafm.facade.permit'].sudo().search([], order='date desc', limit=80)
        return _ok([{
            'id': p.id, 'name': p.name, 'facility': p.facility_id.name or None,
            'zone': p.zone_id.name or None, 'method': p.method,
            'wind_speed': p.wind_speed, 'wind_limit': p.wind_limit,
            'is_safe': p.is_safe, 'state': p.state, 'date': p.date or None,
        } for p in recs])
