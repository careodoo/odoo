# -*- coding: utf-8 -*-
"""واجهة تطبيق مراقبة مراكز التكلفة (cost.center من purchase_limit): إحصائيات
الميزانيات + قائمة المراكز بنِسَب الاستهلاك + تفصيل شهري لكل مركز. للقراءة/المراقبة
على الجوال، مقيّدة بشركات المستخدم. مُغلّفة بفحص وجود الموديل."""
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, API


class CostCenterApi(Controller):

    def _has(self, env):
        return 'cost.center' in env

    def _cids(self, env):
        return env.companies.ids or [env.company.id]

    def _cc_dict(self, c, full=False):
        d = {
            'id': c.id, 'name': c.name,
            'type': c.type if 'type' in c._fields else None,
            'purchase_limit': round(c.purchase_limit or 0, 2) if 'purchase_limit' in c._fields else 0,
            'total': round(c.dash_total or 0, 2) if 'dash_total' in c._fields else 0,
            'used': round(c.dash_used or 0, 2) if 'dash_used' in c._fields else 0,
            'remaining': round(c.dash_remaining or 0, 2) if 'dash_remaining' in c._fields else 0,
            'usage': round(c.dash_usage or 0, 1) if 'dash_usage' in c._fields else 0,
            'start': str(c.budget_start_date or '')[:10] or None if 'budget_start_date' in c._fields else None,
            'end': str(c.budget_end_date or '')[:10] or None if 'budget_end_date' in c._fields else None,
            'months_count': len(c.month_ids) if 'month_ids' in c._fields else 0,
        }
        if full and 'month_ids' in c._fields:
            d['months'] = [{
                'id': m.id, 'label': m.date_string or str(m.date or ''),
                'budget': round(m.budget or 0, 2),
                'extra': round(m.extra_budget or 0, 2),
                'transfer': round(m.transfer_budget or 0, 2),
                'total': round(m.total_budget or 0, 2),
                'used': round(m.used_budget or 0, 2),
                'remaining': round(m.remaining_budget or 0, 2),
                'usage': round((m.used_budget / m.total_budget * 100) if m.total_budget else 0, 1),
                'orders': len(m.purchase_order_ids) if 'purchase_order_ids' in m._fields else 0,
            } for m in c.month_ids.sorted(key=lambda x: x.sequence or 0)]
        return d

    @route(API + '/costcenter/overview', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def overview(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._has(env):
            return _ok({'available': False})
        centers = env['cost.center'].sudo().search([('company_id', 'in', self._cids(env))])
        dicts = [self._cc_dict(c) for c in centers]
        total = sum(d['total'] for d in dicts)
        used = sum(d['used'] for d in dicts)
        return _ok({
            'available': True,
            'stats': {
                'centers': len(dicts),
                'total': round(total, 1), 'used': round(used, 1),
                'remaining': round(total - used, 1),
                'avg_usage': round((used / total * 100) if total else 0, 1),
                'over': sum(1 for d in dicts if d['usage'] >= 90),
            },
        })

    @route(API + '/costcenter/list', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def cc_list(self, type=None, q=None, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._has(env):
            return _ok({'items': []})
        dom = [('company_id', 'in', self._cids(env))]
        if type and 'type' in env['cost.center']._fields:
            dom.append(('type', '=', type))
        if q:
            dom.append(('name', 'ilike', q))
        recs = env['cost.center'].sudo().search(dom, order='id desc', limit=500)
        return _ok({'items': [self._cc_dict(c) for c in recs]})

    @route(API + '/costcenter/<int:cid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def cc_detail(self, cid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._has(env):
            return _err('غير متاح', 404)
        c = env['cost.center'].sudo().browse(cid).exists()
        if not c or c.company_id.id not in self._cids(env):
            return _err('غير موجود', 404)
        return _ok(self._cc_dict(c, full=True))
