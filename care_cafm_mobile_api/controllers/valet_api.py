# -*- coding: utf-8 -*-
"""Valet parking endpoints — the attendant's kerbside console: take a car in,
park it in a bay, answer a retrieval request, hand it back, and close the shift."""
from odoo import fields
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _body, API


class ValetApi(Controller):

    def _facilities(self, env):
        """Sites this person covers: their client's, or the ones they work at."""
        Fac = env['care.cafm.facility'].sudo()
        u = env.user
        if u.has_group('base.group_erp_manager') or u.has_group('base.group_system'):
            return Fac.search([])
        p = u.partner_id
        pids = {p.id}
        if p.commercial_partner_id:
            pids.add(p.commercial_partner_id.id)
            pids.update(env['res.partner'].sudo().search(
                [('commercial_partner_id', '=', p.commercial_partner_id.id)]).ids)
        facs = Fac.search([('partner_id', 'in', list(pids))])
        if facs:
            return facs
        emp = u.employee_id
        ids = set()
        if emp:
            ids |= set(env['care.cafm.workorder'].sudo().search(
                [('employee_id', '=', emp.id)]).mapped('facility_id').ids)
            if 'care.cafm.team' in env:
                ids |= set(env['care.cafm.team'].sudo().search(
                    [('member_ids', 'in', [emp.id])]).mapped('facility_id').ids)
        return Fac.browse(list(ids))

    def _guard(self, env):
        if 'care.valet.ticket' not in env:
            return _err('خدمة صف السيارات غير مفعّلة', 404)
        return None

    def _t(self, t):
        T = t._fields
        return {
            'id': t.id, 'name': t.name, 'plate': t.plate,
            # What the plate already knows: a returning car should not be
            # re-typed, and a standing note must reach the crew every visit.
            'vehicle': ({
                'id': t.vehicle_id.id, 'plate': t.vehicle_id.plate,
                'make': t.vehicle_id.make, 'model': t.vehicle_id.model,
                'color': t.vehicle_id.color,
                'owner': t.vehicle_id.owner_name, 'phone': t.vehicle_id.owner_phone,
                'owner_type': t.vehicle_id.owner_type,
                'visits': t.vehicle_id.visit_count,
                'regular': t.vehicle_id.is_regular,
                'vip': t.vehicle_id.vip, 'blocked': t.vehicle_id.blocked,
                'block_reason': t.vehicle_id.block_reason or None,
                'notes': t.vehicle_id.notes or None,
                'avg_stay': round(t.vehicle_id.avg_stay_minutes),
                'last_seen': str(t.vehicle_id.last_seen or '')[:16] or None,
            } if t.vehicle_id else None),
            'visit_number': t.visit_number,
            'car': ' '.join(filter(None, [t.car_make, t.car_model, t.car_color])) or None,
            'car_make': t.car_make or None, 'car_model': t.car_model or None,
            'car_color': t.car_color or None, 'key_tag': t.key_tag or None,
            'guest': t.guest_name or None, 'phone': t.guest_phone or None,
            'facility': t.facility_id.name or None, 'facility_id': t.facility_id.id or None,
            'zone': t.zone_id.name or None, 'zone_id': t.zone_id.id or None,
            'spot': t.spot_id.name or None, 'spot_id': t.spot_id.id or None,
            'state': t.state, 'state_label': dict(T['state'].selection).get(t.state, t.state),
            'received_at': str(t.received_at)[:16] if t.received_at else None,
            'requested_at': str(t.requested_at)[:16] if t.requested_at else None,
            'delivered_at': str(t.delivered_at)[:16] if t.delivered_at else None,
            'retrieval_minutes': round(t.retrieval_minutes, 1),
            'park_minutes': round(t.park_minutes, 1),
            'sla_minutes': t.sla_minutes, 'is_late': t.is_late,
            'fee': t.fee, 'tip': t.tip, 'paid': t.paid,
            'payment_method': t.payment_method,
            'has_damage': t.has_damage, 'damage_note': t.damage_note or None,
            'received_by': t.received_by.sudo().name or None,
            'delivered_by': t.delivered_by.sudo().name or None,
        }

    # ---- the console ------------------------------------------------------
    @route(API + '/valet/board', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def board(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        facs = self._facilities(env)
        T = env['care.valet.ticket'].sudo()
        Z = env['care.valet.zone'].sudo()
        today = fields.Date.context_today(env.user)
        live = T.search([('facility_id', 'in', facs.ids),
                         ('state', 'in', ('received', 'parked', 'requested'))],
                        order='requested_at desc, received_at desc', limit=200)
        done_today = T.search_count([('facility_id', 'in', facs.ids), ('state', '=', 'delivered'),
                                     ('delivered_at', '>=', '%s 00:00:00' % today)])
        zones = Z.search([('facility_id', 'in', facs.ids)])
        # the attendant's own open shift, if any
        emp = env.user.employee_id
        shift = env['care.valet.shift'].sudo().search(
            [('employee_id', '=', emp.id), ('state', '=', 'open')], limit=1) if emp else None
        return _ok({
            'available': True,
            'stats': {
                'received': len(live.filtered(lambda x: x.state == 'received')),
                'parked': len(live.filtered(lambda x: x.state == 'parked')),
                'requested': len(live.filtered(lambda x: x.state == 'requested')),
                'delivered_today': done_today,
                'late': len(live.filtered('is_late')),
            },
            'zones': [{'id': z.id, 'name': z.name, 'facility': z.facility_id.name or None,
                       'capacity': z.capacity, 'occupied': z.occupied, 'free': z.free,
                       'occupancy': z.occupancy,
                       'spots': [{'id': s.id, 'name': s.name, 'state': s.state}
                                 for s in z.spot_ids]} for z in zones],
            'facilities': [{'id': f.id, 'name': f.name} for f in facs],
            'shift': ({'id': shift.id, 'name': shift.name, 'tickets': shift.ticket_count,
                       'fees': shift.total_fees, 'tips': shift.total_tips,
                       'cash_due': shift.cash_due} if shift else None),
            'tickets': [self._t(t) for t in live],
        })

    @route(API + '/valet/tickets', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def tickets(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        a = request.httprequest.args
        dom = [('facility_id', 'in', self._facilities(env).ids)]
        st = a.get('state')
        if st == 'live':
            dom.append(('state', 'in', ('received', 'parked', 'requested')))
        elif st and st != 'all':
            dom.append(('state', '=', st))
        q = (a.get('q') or '').strip()
        if q:
            dom += ['|', '|', ('plate', 'ilike', q), ('name', 'ilike', q), ('guest_name', 'ilike', q)]
        recs = env['care.valet.ticket'].sudo().search(dom, limit=200)
        return _ok([self._t(t) for t in recs])

    @route(API + '/valet/ticket/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        b = _body()
        plate = (b.get('plate') or '').strip()
        if not plate:
            return _err('رقم اللوحة مطلوب', 422)
        facs = self._facilities(env)
        fid = int(b['facility_id']) if b.get('facility_id') else (facs[:1].id or None)
        if not fid or fid not in facs.ids:
            return _err('المرفق مطلوب', 422)
        emp = env.user.employee_id
        shift = env['care.valet.shift'].sudo().search(
            [('employee_id', '=', emp.id), ('state', '=', 'open')], limit=1) if emp else None
        vals = {
            'plate': plate, 'facility_id': fid,
            'car_make': b.get('car_make') or False, 'car_model': b.get('car_model') or False,
            'car_color': b.get('car_color') or False, 'key_tag': b.get('key_tag') or False,
            'guest_name': b.get('guest') or False, 'guest_phone': b.get('phone') or False,
            'damage_note': b.get('damage_note') or False,
            'fee': float(b.get('fee') or 0), 'received_by': emp.id if emp else False,
            'zone_id': int(b['zone_id']) if b.get('zone_id') else False,
            'shift_id': shift.id if shift else False,
        }
        t = env['care.valet.ticket'].sudo().create(vals)
        return _ok(self._t(t))

    @route(API + '/valet/ticket/<int:tid>/<string:act>', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def action(self, tid, act, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        t = env['care.valet.ticket'].sudo().browse(tid).exists()
        if not t or t.facility_id.id not in self._facilities(env).ids:
            return _err('التذكرة غير موجودة', 404)
        b = _body()
        emp = env.user.employee_id
        try:
            if act == 'park':
                spot = int(b['spot_id']) if b.get('spot_id') else None
                if spot:
                    t.spot_id = spot
                t.parked_by = emp.id if emp else False
                t.action_park()
            elif act == 'request':
                t.action_request()
            elif act == 'deliver':
                t.action_deliver(by=(emp.id if emp else None),
                                 fee=(float(b['fee']) if b.get('fee') is not None else None),
                                 tip=(float(b['tip']) if b.get('tip') is not None else None),
                                 paid=(bool(b['paid']) if 'paid' in b else None))
            elif act == 'cancel':
                t.action_cancel()
            else:
                return _err('إجراء غير معروف', 400)
        except Exception as e:
            return _err(str(e), 422)
        return _ok(self._t(t))

    # ---- shifts -----------------------------------------------------------
    @route(API + '/valet/shift/<string:act>', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def shift(self, act, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        emp = env.user.employee_id
        if not emp:
            return _err('لا يوجد ملف موظف مرتبط', 422)
        S = env['care.valet.shift'].sudo()
        cur = S.search([('employee_id', '=', emp.id), ('state', '=', 'open')], limit=1)
        if act == 'open':
            if cur:
                return _ok({'id': cur.id, 'name': cur.name, 'already': True})
            facs = self._facilities(env)
            b = _body()
            fid = int(b['facility_id']) if b.get('facility_id') else (facs[:1].id or None)
            if not fid:
                return _err('المرفق مطلوب', 422)
            s = S.create({'employee_id': emp.id, 'facility_id': fid})
            return _ok({'id': s.id, 'name': s.name})
        if act == 'close':
            if not cur:
                return _err('لا توجد وردية مفتوحة', 404)
            cur.action_close()
            return _ok({'id': cur.id, 'name': cur.name, 'tickets': cur.ticket_count,
                        'fees': cur.total_fees, 'tips': cur.total_tips, 'cash_due': cur.cash_due})
        return _err('إجراء غير معروف', 400)

    # A Kuwaiti plate often contains a slash, which cannot survive in a path
    # segment, so the plate travels as a query parameter.
    @route([API + '/valet/plate', API + '/valet/plate/<path:plate>'], type='http',
           auth='public', methods=['GET'], csrf=False, cors='*')
    def valet_plate_lookup(self, plate=None, **kw):
        """What do we already know about this plate?

        Called the moment the camera reads one, so the crew sees the car's
        history before the guest has finished handing over the key. An unknown
        plate is an ordinary answer, not an error.
        """
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        plate = plate or kw.get('plate') or request.httprequest.args.get('plate')
        if not plate:
            return _err('أدخل رقم اللوحة', 422)
        v = env['care.valet.vehicle'].sudo().find_by_plate(plate)
        if not v:
            return _ok({'known': False, 'plate': plate})
        recent = env['care.valet.ticket'].sudo().search(
            [('vehicle_id', '=', v.id)], order='received_at desc', limit=8)
        return _ok({
            'known': True, 'id': v.id, 'plate': v.plate,
            'make': v.make, 'model': v.model, 'color': v.color,
            'owner': v.owner_name, 'phone': v.owner_phone,
            'owner_type': v.owner_type, 'visits': v.visit_count,
            'regular': v.is_regular, 'vip': v.vip,
            'blocked': v.blocked, 'block_reason': v.block_reason or None,
            'notes': v.notes or None,
            'avg_stay': round(v.avg_stay_minutes),
            'last_seen': str(v.last_seen or '')[:16] or None,
            'preferred_zone': v.preferred_zone_id.name or None,
            'history': [{
                'id': t.id, 'name': t.name, 'state': t.state,
                'received_at': str(t.received_at or '')[:16],
                'delivered_at': str(t.delivered_at or '')[:16] or None,
                'zone': t.zone_id.name or None,
            } for t in recent],
        })
