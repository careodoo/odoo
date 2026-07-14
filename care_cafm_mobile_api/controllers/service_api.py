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
        recs = env['care.cafm.clean.audit'].sudo().search([], order='audit_date desc', limit=80)
        return _ok([{
            'id': a.id, 'name': a.name, 'facility': a.facility_id.name or None,
            'location': a.location_id.name or None,
            'score': round(a.score, 1), 'rating': a.rating,
            'fail_count': a.fail_count, 'state': a.state,
            'date': a.audit_date or None,
        } for a in recs])

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
