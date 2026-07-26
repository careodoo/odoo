# -*- coding: utf-8 -*-
"""واجهة تطبيق موديول البترول/خزّانات الوقود (care_petrol) — كاملة بكل الحقول:
الخزّانات + المداولات الداخلية (شحن Charges / استهلاك Uses / تحويل Transfers) +
المراحل Stages، مع إحصائيات غنية للهيدر وفلاتر متعدّدة ونماذج إضافة مطابقة تماماً
لحقول الباك ايند. كل الوصول عبر sudo ومقيّد بشركات المستخدم."""
from odoo import fields
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _body, API


def _d(v):
    return str(v) if v else None


def _dt(v):
    return str(v)[:16] if v else None


class PetrolApi(Controller):

    # ---- أدوات مساعدة -----------------------------------------------------
    def _has(self, env):
        return 'petrol.tank' in env

    def _cids(self, env):
        return env.companies.ids or [env.company.id]

    def _tank_dict(self, t, full=False):
        d = {
            'id': t.id, 'name': t.name,
            'capacity': round(t.capacity or 0, 2),
            'used': round(t.used or 0, 2),
            'charged': round(t.charged or 0, 2),
            'incoming_transfer': round(t.positive_transferred or 0, 2),
            'outgoing_transfer': round(t.negative_transferred or 0, 2),
            'transferred': round(t.transferred or 0, 2),
            'balance': round(t.balance or 0, 2),
            'balance_progress': round(t.balance_progress or 0, 1),
            'fill_pct': round((t.balance / t.capacity * 100) if t.capacity else 0, 1),
            'last_charge': _d(t.last_charge),
            'first_charge_balance': round(t.first_charge_balance or 0, 2),
            'stage_id': t.stage_id.id if t.stage_id else None,
            'stage': t.stage_id.name if t.stage_id else None,
            'company': t.company_id.name if t.company_id else None,
            'charges_count': len(t.charge_ids),
            'uses_count': len(t.use_ids),
            'transfers_count': len(t.transfer_ids),
            'low': bool(t.capacity) and (t.balance or 0) < (t.capacity * 0.2),
        }
        if full:
            d['charges'] = [self._charge_dict(c) for c in t.charge_ids]
            d['uses'] = [self._use_dict(u) for u in t.use_ids]
            d['transfers'] = [self._transfer_dict(x) for x in t.transfer_ids]
        return d

    def _charge_dict(self, c):
        return {
            'id': c.id, 'name': c.name,
            'tank_id': c.tank_id.id if c.tank_id else None,
            'tank': c.tank_id.name if c.tank_id else None,
            'charge_date': _d(c.charge_date),
            'quantity': round(c.quantity or 0, 2),
            'cost': round(c.cost or 0, 2),
            'company': c.company_id.name if c.company_id else None,
        }

    def _use_dict(self, u):
        return {
            'id': u.id, 'name': u.name,
            'tank_id': u.tank_id.id if u.tank_id else None,
            'tank': u.tank_id.name if u.tank_id else None,
            'vehicle_id': u.vehicle_id.id if u.vehicle_id else None,
            'vehicle': u.vehicle_id.name if u.vehicle_id else None,
            'odometer_value': round(u.odometer_value or 0, 2),
            'current_quantity': round(u.current_quantity or 0, 2),
            'quantity': round(u.quantity or 0, 2),
            'use_quantity': round(u.use_quantity or 0, 2),
            'datetime': _dt(u.datetime),
            'last_odometer': round(u.last_odometer or 0, 2),
            'last_quantity': round(u.last_quantity or 0, 2),
            'used_odometer': round(u.used_odometer or 0, 2),
            'used_quantity': round(u.used_quantity or 0, 2),
            'liter_per_km_rate': round(u.liter_per_km_rate or 0, 3),
            'company': u.company_id.name if u.company_id else None,
        }

    def _transfer_dict(self, x):
        return {
            'id': x.id,
            'tank_id': x.tank_id.id if x.tank_id else None,
            'tank': x.tank_id.name if x.tank_id else None,
            'from_tank_id': x.from_tank_id.id if x.from_tank_id else None,
            'from_tank': x.from_tank_id.name if x.from_tank_id else None,
            'to_tank_id': x.to_tank_id.id if x.to_tank_id else None,
            'to_tank': x.to_tank_id.name if x.to_tank_id else None,
            'quantity': round(x.quantity or 0, 2),
            'date': _d(x.date),
            'state': x.state,
            'state_label': dict(x._fields['state'].selection).get(x.state, x.state),
            'create_from': x.create_from,
            'company': x.company_id.name if x.company_id else None,
        }

    # ---- نظرة عامة + إحصائيات الهيدر --------------------------------------
    @route(API + '/petrol/overview', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def overview(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._has(env):
            return _ok({'available': False})
        cids = self._cids(env)
        T = env['petrol.tank'].sudo()
        C = env['petrol.tank.charge'].sudo()
        U = env['petrol.tank.use'].sudo()
        X = env['petrol.tank.transfer'].sudo()
        dom = [('company_id', 'in', cids)]
        tanks = T.search(dom)
        cap = sum(tanks.mapped('capacity'))
        bal = sum(tanks.mapped('balance'))
        charged = sum(tanks.mapped('charged'))
        used = sum(tanks.mapped('used'))
        incoming = sum(tanks.mapped('positive_transferred'))
        outgoing = sum(tanks.mapped('negative_transferred'))
        low = tanks.filtered(lambda t: t.capacity and t.balance < t.capacity * 0.2)
        last = tanks.filtered('last_charge').sorted(key=lambda t: t.last_charge, reverse=True)
        stats = {
            'tanks': len(tanks),
            'capacity': round(cap, 1),
            'balance': round(bal, 1),
            'charged': round(charged, 1),
            'used': round(used, 1),
            'incoming': round(incoming, 1),
            'outgoing': round(outgoing, 1),
            'transferred': round(incoming + outgoing, 1),
            'avg_fill': round((bal / cap * 100) if cap else 0, 1),
            'low_tanks': len(low),
            'charges': C.search_count(dom),
            'uses': U.search_count(dom),
            'transfers': X.search_count(dom),
            'pending_transfers': X.search_count(dom + [('state', '=', 'draft')]),
            'last_charge': _d(last[0].last_charge) if last else None,
        }
        return _ok({
            'available': True,
            'stats': stats,
            'stages': [{'id': s.id, 'name': s.name} for s in env['petrol.tank.stage'].sudo().search([('company_id', 'in', cids)])],
            'low_tanks': [self._tank_dict(t) for t in low[:10]],
        })

    @route(API + '/petrol/options', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def options(self, **kw):
        """قوائم المنسدلات للنماذج: الخزّانات، المراحل، المركبات."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._has(env):
            return _ok({'tanks': [], 'stages': [], 'vehicles': []})
        cids = self._cids(env)
        tanks = env['petrol.tank'].sudo().search([('company_id', 'in', cids)])
        vehicles = env['fleet.vehicle'].sudo().search([], limit=1000) if 'fleet.vehicle' in env else env['petrol.tank'].sudo().browse()
        return _ok({
            'tanks': [{'id': t.id, 'name': t.name, 'balance': round(t.balance or 0, 1), 'capacity': round(t.capacity or 0, 1)} for t in tanks],
            'stages': [{'id': s.id, 'name': s.name} for s in env['petrol.tank.stage'].sudo().search([('company_id', 'in', cids)])],
            'vehicles': [{'id': v.id, 'name': v.name} for v in vehicles],
        })

    # ---- قوائم مع فلاتر ---------------------------------------------------
    @route(API + '/petrol/tanks', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def tanks(self, stage=None, low=None, q=None, sort=None, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._has(env):
            return _ok({'items': []})
        dom = [('company_id', 'in', self._cids(env))]
        if stage:
            dom.append(('stage_id', '=', int(stage)))
        if q:
            dom.append(('name', 'ilike', q))
        order = {'balance': 'balance desc', 'capacity': 'capacity desc', 'name': 'name'}.get(sort, 'id desc')
        recs = env['petrol.tank'].sudo().search(dom, order=order, limit=300)
        items = [self._tank_dict(t) for t in recs]
        if low in ('1', 'true', 'True'):
            items = [i for i in items if i['low']]
        return _ok({'items': items})

    @route(API + '/petrol/tank/<int:tid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def tank_detail(self, tid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._has(env):
            return _err('غير متاح', 404)
        t = env['petrol.tank'].sudo().browse(tid).exists()
        if not t or t.company_id.id not in self._cids(env):
            return _err('غير موجود', 404)
        return _ok(self._tank_dict(t, full=True))

    @route(API + '/petrol/charges', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def charges(self, tank=None, date_from=None, date_to=None, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._has(env):
            return _ok({'items': []})
        dom = [('company_id', 'in', self._cids(env))]
        if tank:
            dom.append(('tank_id', '=', int(tank)))
        if date_from:
            dom.append(('charge_date', '>=', date_from))
        if date_to:
            dom.append(('charge_date', '<=', date_to))
        recs = env['petrol.tank.charge'].sudo().search(dom, order='id desc', limit=500)
        return _ok({'items': [self._charge_dict(c) for c in recs],
                    'total_qty': round(sum(recs.mapped('quantity')), 1),
                    'total_cost': round(sum(recs.mapped('cost')), 1)})

    @route(API + '/petrol/uses', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def uses(self, tank=None, vehicle=None, date_from=None, date_to=None, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._has(env):
            return _ok({'items': []})
        dom = [('company_id', 'in', self._cids(env))]
        if tank:
            dom.append(('tank_id', '=', int(tank)))
        if vehicle:
            dom.append(('vehicle_id', '=', int(vehicle)))
        if date_from:
            dom.append(('datetime', '>=', date_from + ' 00:00:00'))
        if date_to:
            dom.append(('datetime', '<=', date_to + ' 23:59:59'))
        recs = env['petrol.tank.use'].sudo().search(dom, order='id desc', limit=500)
        return _ok({'items': [self._use_dict(u) for u in recs],
                    'total_qty': round(sum(recs.mapped('quantity')), 1)})

    @route(API + '/petrol/transfers', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def transfers(self, tank=None, state=None, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._has(env):
            return _ok({'items': []})
        dom = [('company_id', 'in', self._cids(env))]
        if tank:
            dom.append(('tank_id', '=', int(tank)))
        if state in ('draft', 'done'):
            dom.append(('state', '=', state))
        recs = env['petrol.tank.transfer'].sudo().search(dom, order='id desc', limit=500)
        return _ok({'items': [self._transfer_dict(x) for x in recs],
                    'total_qty': round(sum(recs.mapped('quantity')), 1)})

    # ---- إنشاء (حقول مطابقة للباك ايند) -----------------------------------
    @route(API + '/petrol/tank/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def tank_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._has(env):
            return _err('غير متاح', 404)
        b = _body() or {}
        if not (b.get('name') or '').strip():
            return _err('الاسم مطلوب', 400)
        vals = {'name': b['name'].strip(), 'capacity': float(b.get('capacity') or 0)}
        if b.get('stage_id'):
            vals['stage_id'] = int(b['stage_id'])
        try:
            rec = env['petrol.tank'].sudo().create(vals)
        except Exception as e:
            return _err('تعذّر إنشاء الخزّان: %s' % e, 400)
        return _ok(self._tank_dict(rec))

    @route(API + '/petrol/charge/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def charge_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._has(env):
            return _err('غير متاح', 404)
        b = _body() or {}
        if not b.get('tank_id'):
            return _err('الخزّان مطلوب', 400)
        vals = {
            'tank_id': int(b['tank_id']),
            'quantity': float(b.get('quantity') or 0),
            'cost': float(b.get('cost') or 0),
        }
        if b.get('charge_date'):
            vals['charge_date'] = b['charge_date']
        try:
            rec = env['petrol.tank.charge'].sudo().create(vals)
        except Exception as e:
            return _err('تعذّر تسجيل الشحن: %s' % e, 400)
        return _ok(self._charge_dict(rec))

    @route(API + '/petrol/use/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def use_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._has(env):
            return _err('غير متاح', 404)
        b = _body() or {}
        if not b.get('vehicle_id'):
            return _err('المركبة مطلوبة', 400)
        vals = {
            'vehicle_id': int(b['vehicle_id']),
            'odometer_value': float(b.get('odometer_value') or 0),
            'current_quantity': float(b.get('current_quantity') or 0),
            'quantity': float(b.get('quantity') or 0),
        }
        if b.get('tank_id'):
            vals['tank_id'] = int(b['tank_id'])
        if b.get('datetime'):
            vals['datetime'] = b['datetime']
        try:
            rec = env['petrol.tank.use'].sudo().create(vals)
        except Exception as e:
            return _err('تعذّر تسجيل الاستهلاك: %s' % e, 400)
        return _ok(self._use_dict(rec))

    @route(API + '/petrol/transfer/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def transfer_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._has(env):
            return _err('غير متاح', 404)
        b = _body() or {}
        if not (b.get('tank_id') and b.get('to_tank_id')):
            return _err('الخزّان المصدر والوجهة مطلوبان', 400)
        vals = {
            'tank_id': int(b['tank_id']),
            'to_tank_id': int(b['to_tank_id']),
            'quantity': float(b.get('quantity') or 0),
            'create_from': 'tank',
        }
        if b.get('date'):
            vals['date'] = b['date']
        try:
            rec = env['petrol.tank.transfer'].sudo().create(vals)
            if b.get('confirm'):
                rec.button_transfer()
        except Exception as e:
            return _err('تعذّر التحويل: %s' % e, 400)
        return _ok(self._transfer_dict(rec))

    @route('/cafm/petrol/export', type='http', auth='public', methods=['GET'], csrf=False)
    def petrol_export(self, kind='tanks', **kw):
        """تصدير بيانات البترول إلى Excel (خزّانات/شحن/استهلاك/تحويلات)."""
        from odoo import _
        from .client_api import _xlsx_response, _report_env
        env = _report_env()
        if not env:
            return request.redirect('/web/login')
        if not self._has(env):
            return request.not_found()
        cids = self._cids(env)
        if kind == 'charges':
            recs = env['petrol.tank.charge'].sudo().search([('company_id', 'in', cids)], order='id desc', limit=10000)
            columns = [_('المرجع'), _('الخزّان'), _('التاريخ'), _('الكمية'), _('التكلفة')]
            rows = [[c.name, c.tank_id.name or '', str(c.charge_date or ''), c.quantity, c.cost] for c in recs]
            title = _('شحن الوقود')
        elif kind == 'uses':
            recs = env['petrol.tank.use'].sudo().search([('company_id', 'in', cids)], order='id desc', limit=10000)
            columns = [_('المرجع'), _('المركبة'), _('الخزّان'), _('الكمية'), _('العدّاد'), _('ل/كم')]
            rows = [[u.name, u.vehicle_id.name or '', u.tank_id.name or '', u.quantity, u.odometer_value, round(u.liter_per_km_rate or 0, 3)] for u in recs]
            title = _('استهلاك الوقود')
        elif kind == 'transfers':
            recs = env['petrol.tank.transfer'].sudo().search([('company_id', 'in', cids)], order='id desc', limit=10000)
            sel = dict(env['petrol.tank.transfer']._fields['state'].selection)
            columns = [_('من'), _('إلى'), _('الكمية'), _('التاريخ'), _('الحالة')]
            rows = [[x.from_tank_id.name or '', x.to_tank_id.name or '', x.quantity, str(x.date or ''), sel.get(x.state, x.state)] for x in recs]
            title = _('تحويلات الوقود')
        else:
            recs = env['petrol.tank'].sudo().search([('company_id', 'in', cids)], order='id desc')
            columns = [_('الخزّان'), _('المرحلة'), _('السعة'), _('الرصيد'), _('نسبة الامتلاء %'), _('المشحون'), _('المستهلك'), _('آخر شحن')]
            rows = [[t.name, t.stage_id.name or '', t.capacity, t.balance,
                     round((t.balance / t.capacity * 100) if t.capacity else 0, 1), t.charged, t.used, str(t.last_charge or '')] for t in recs]
            title = _('خزّانات الوقود')
        return _xlsx_response(title, columns, rows, 'petrol-%s.xlsx' % kind, [(_('العدد'), len(recs))])

    @route(API + '/petrol/transfer/<int:xid>/confirm', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def transfer_confirm(self, xid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._has(env):
            return _err('غير متاح', 404)
        x = env['petrol.tank.transfer'].sudo().browse(xid).exists()
        if not x:
            return _err('غير موجود', 404)
        try:
            x.button_transfer()
        except Exception as e:
            return _err('تعذّر التأكيد: %s' % e, 400)
        return _ok(self._transfer_dict(x))
