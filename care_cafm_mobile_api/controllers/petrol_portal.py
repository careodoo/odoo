# -*- coding: utf-8 -*-
"""بورتال ويب لموديول البترول/الوقود (/my/petrol) — تكافؤ مع شاشة التطبيق:
إحصائيات + بطاقات خزّانات بأشرطة امتلاء + أحدث الشحن/الاستهلاك/التحويلات. يعيد
استخدام منطق PetrolApi (نفس القواميس والنطاق)."""
from odoo.http import request, route

from .petrol_api import PetrolApi


class PetrolPortal(PetrolApi):

    @route(['/my/petrol'], type='http', auth='user', website=True)
    def portal_petrol(self, **kw):
        env = request.env
        if not self._has(env):
            return request.render('care_cafm_mobile_api.portal_petrol', {'available': False})
        cids = self._cids(env)
        T = env['petrol.tank'].sudo()
        tanks = T.search([('company_id', 'in', cids)], order='id desc')
        tank_dicts = [self._tank_dict(t) for t in tanks]
        cap = sum(t['capacity'] for t in tank_dicts)
        bal = sum(t['balance'] for t in tank_dicts)
        charges = env['petrol.tank.charge'].sudo().search([('company_id', 'in', cids)], order='id desc', limit=15)
        uses = env['petrol.tank.use'].sudo().search([('company_id', 'in', cids)], order='id desc', limit=15)
        transfers = env['petrol.tank.transfer'].sudo().search([('company_id', 'in', cids)], order='id desc', limit=15)
        return request.render('care_cafm_mobile_api.portal_petrol', {
            'available': True,
            'stats': {
                'tanks': len(tank_dicts),
                'capacity': round(cap, 1), 'balance': round(bal, 1),
                'avg_fill': round((bal / cap * 100) if cap else 0, 1),
                'charged': round(sum(t['charged'] for t in tank_dicts), 1),
                'used': round(sum(t['used'] for t in tank_dicts), 1),
                'low': sum(1 for t in tank_dicts if t['low']),
            },
            'tanks': tank_dicts,
            'charges': [self._charge_dict(c) for c in charges],
            'uses': [self._use_dict(u) for u in uses],
            'transfers': [self._transfer_dict(x) for x in transfers],
        })
