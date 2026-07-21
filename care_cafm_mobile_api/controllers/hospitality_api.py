# -*- coding: utf-8 -*-
"""Hospitality endpoints — the ordering side for the app, plus the kitchen queue.

Mirrors what the web portal already does at /hosp, so a requester on a phone and
one at a desk see the same menu, the same allowance, and the same live status.
"""
from odoo import fields
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _body, API


def _base():
    return request.env['ir.config_parameter'].sudo().get_param(
        'web.base.url', '').rstrip('/')


class HospitalityApi(Controller):

    # ---- scoping ----------------------------------------------------------
    def _facilities(self, env):
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
        if 'care.hosp.order' not in env:
            return _err('خدمة الضيافة غير مفعّلة', 404)
        return None

    def _order(self, o):
        T = o._fields
        return {
            'id': o.id, 'name': o.name,
            'state': o.state, 'state_label': dict(T['state'].selection).get(o.state, o.state),
            'requester': o.requester_id.sudo().name,
            'room': o.room_label or o.location_id.name or None,
            'facility': o.facility_id.name,
            'order_type': o.order_type, 'guest_count': o.guest_count,
            'guest_name': o.guest_name or None, 'is_vip': o.is_vip,
            'placed_at': str(o.placed_at)[:16] if o.placed_at else None,
            'ready_at': str(o.ready_at)[:16] if o.ready_at else None,
            'delivered_at': str(o.delivered_at)[:16] if o.delivered_at else None,
            'wait_minutes': round(o.wait_minutes, 1), 'prep_target': o.prep_target,
            'is_late': o.is_late, 'item_count': o.item_count,
            'total_cost': round(o.total_cost, 3), 'rating': o.rating,
            'note': o.note or None, 'limit_note': o.limit_note or None,
            'lines': [{
                'id': l.id, 'item': l.item_id.name, 'icon': l.item_id.icon or '☕',
                'qty': l.quantity, 'options': l.option_label or None,
                'note': l.note or None, 'station': l.station_id.name or None,
                'cost': round(l.line_cost, 3),
            } for l in o.line_ids],
        }

    # ---- menu -------------------------------------------------------------
    @route(API + '/hosp/menu', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def menu(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        facs = self._facilities(env)
        items = env['care.hosp.item'].sudo().search([('available', '=', True)])
        items = items.filtered(lambda i: not i.facility_ids or (i.facility_ids & facs))
        cats = env['care.hosp.category'].sudo().search([])
        favs = env['care.hosp.favorite'].sudo().search(
            [('user_id', '=', env.user.id)], order='times_used desc', limit=8)
        usage = env['care.hosp.limit'].sudo().usage_for(env.user, facs[:1] or None)
        return _ok({
            'available': True,
            'facilities': [{'id': f.id, 'name': f.name} for f in facs],
            # Where this person is served, so the order sheet arrives filled in
            # instead of asking for an office number every single time.
            'my_place': {
                'location_id': env.user.hosp_location_id.id or None,
                'location': env.user.hosp_location_id.name or None,
                'code': env.user.hosp_location_id.code or None,
                'room_label': env.user.hosp_room_label or None,
                'locked': env.user.hosp_location_locked,
            },
            'places': [{'id': l.id, 'name': l.name, 'code': l.code or None}
                       for l in env['care.cafm.location'].sudo().search(
                           [('facility_id', 'in', facs.ids)], limit=400)],
            'categories': [{'id': c.id, 'name': c.name, 'icon': c.icon or '☕',
                            'color': c.color or '#8a6d3b', 'sequence': c.sequence}
                           for c in cats],
            'items': [{
                'id': i.id, 'name': i.name, 'icon': i.icon or '☕',
                'category_id': i.category_id.id, 'category': i.category_id.name,
                'description': i.description or None,
                # A menu is looked at before it is read. The URL is served by
                # Odoo's image endpoint so the payload stays small and the
                # phone can cache each photo.
                'image': ('%s/web/image/care.hosp.item/%s/image/400x400'
                          % (_base(), i.id)) if i.image else None,
                'prep_minutes': i.prep_minutes, 'cost': i.unit_cost,
                # a breakfast item outside its serving window must not look orderable
                'servable': i.is_servable_now(),
                'serve_from': i.serve_from, 'serve_to': i.serve_to,
                'option_groups': [{
                    'id': grp.id, 'name': grp.name, 'required': grp.required,
                    'multi': grp.multi, 'max_select': grp.max_select,
                    'options': [{'id': o.id, 'name': o.name, 'extra_cost': o.extra_cost,
                                 'is_default': o.is_default}
                                for o in grp.option_ids.sorted('sequence')],
                } for grp in i.option_group_ids.sorted('sequence')],
            } for i in items.sorted(lambda x: (x.category_id.sequence, x.sequence))],
            'favorites': [{'id': f.id, 'name': f.name, 'item': f.item_id.name,
                           'icon': f.item_id.icon or '☕',
                           'options': ' · '.join(f.option_ids.mapped('name')) or None,
                           'qty': f.quantity} for f in favs],
            'limits': usage,
        })

    # ---- ordering ---------------------------------------------------------
    @route(API + '/hosp/order/create', type='http', auth='public', methods=['POST'],
           csrf=False, cors='*')
    def create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        b = _body()
        facs = self._facilities(env)
        fid = int(b['facility_id']) if b.get('facility_id') else (facs[:1].id or None)
        if not fid or fid not in facs.ids:
            return _err('المرفق مطلوب', 422)
        lines = b.get('lines') or []
        if not lines:
            return _err('أضف صنفًا واحدًا على الأقل', 422)
        emp = env.user.employee_id
        vals = {
            'requester_id': env.user.id, 'facility_id': fid,
            'room_label': (b.get('room') or env.user.hosp_room_label
                           or env.user.hosp_location_id.name or False),
            'location_id': (int(b['location_id']) if b.get('location_id')
                            else env.user.hosp_location_id.id or False),
            'note': b.get('note') or False,
            'order_type': b.get('order_type') or 'self',
            'guest_count': int(b.get('guest_count') or 1),
            'guest_name': b.get('guest_name') or False,
            'is_vip': bool(b.get('is_vip')),
            'department_id': emp.department_id.id if emp and emp.department_id else False,
            'line_ids': [(0, 0, {
                'item_id': int(l['item_id']),
                'quantity': float(l.get('qty') or 1),
                'option_ids': [(6, 0, [int(x) for x in (l.get('options') or [])])],
                'note': l.get('note') or False,
            }) for l in lines],
        }
        o = env['care.hosp.order'].sudo().create(vals)
        try:
            o.action_place()
        except Exception as e:
            msg = str(getattr(e, 'args', [e])[0] if getattr(e, 'args', None) else e)
            o.action_cancel()
            return _err(msg, 422)
        if b.get('save_favorite') and lines:
            l = lines[0]
            env['care.hosp.favorite'].sudo().create({
                'name': b.get('favorite_name') or o.line_ids[:1].item_id.name,
                'user_id': env.user.id, 'item_id': int(l['item_id']),
                'option_ids': [(6, 0, [int(x) for x in (l.get('options') or [])])],
                'quantity': float(l.get('qty') or 1),
            })
        return _ok(self._order(o))

    @route(API + '/hosp/orders', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def my_orders(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        O = env['care.hosp.order'].sudo()
        recs = O.search([('requester_id', '=', env.user.id), ('state', '!=', 'draft')], limit=60)
        live = recs.filtered(lambda o: o.state in ('await_approval', 'placed', 'accepted',
                                                   'preparing', 'ready'))
        return _ok({'live': [self._order(o) for o in live],
                    'past': [self._order(o) for o in (recs - live)[:40]]})

    @route(API + '/hosp/order/<int:oid>/rate', type='http', auth='public', methods=['POST'],
           csrf=False, cors='*')
    def rate(self, oid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        o = env['care.hosp.order'].sudo().browse(oid).exists()
        if not o or o.requester_id.id != env.user.id:
            return _err('الطلب غير موجود', 404)
        b = _body()
        o.write({'rating': str(b.get('rating') or '5'),
                 'rating_note': b.get('note') or False})
        return _ok(self._order(o))

    @route(API + '/hosp/order/<int:oid>/cancel', type='http', auth='public', methods=['POST'],
           csrf=False, cors='*')
    def cancel(self, oid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        o = env['care.hosp.order'].sudo().browse(oid).exists()
        if not o or o.requester_id.id != env.user.id:
            return _err('الطلب غير موجود', 404)
        o.action_cancel()
        return _ok(self._order(o))

    @route(API + '/hosp/favorite/<int:fid>/order', type='http', auth='public', methods=['POST'],
           csrf=False, cors='*')
    def fav_order(self, fid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        f = env['care.hosp.favorite'].sudo().browse(fid).exists()
        if not f or f.user_id.id != env.user.id:
            return _err('غير موجود', 404)
        facs = self._facilities(env)
        if not facs:
            return _err('لا مرفق متاح', 422)
        o = env['care.hosp.order'].sudo().create({
            'requester_id': env.user.id, 'facility_id': facs[0].id,
            'room_label': _body().get('room') or False,
            'line_ids': [(0, 0, {'item_id': f.item_id.id, 'quantity': f.quantity or 1,
                                 'option_ids': [(6, 0, f.option_ids.ids)],
                                 'note': f.note or False})],
        })
        try:
            o.action_place()
        except Exception as e:
            o.action_cancel()
            return _err(str(getattr(e, 'args', [e])[0] if getattr(e, 'args', None) else e), 422)
        f.times_used += 1
        return _ok(self._order(o))

    # ---- kitchen ----------------------------------------------------------
    @route(API + '/hosp/kitchen', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def kitchen(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        facs = self._facilities(env)
        O = env['care.hosp.order'].sudo()
        live = O.search([('facility_id', 'in', facs.ids),
                         ('state', 'in', ('placed', 'accepted', 'preparing', 'ready'))],
                        order='placed_at asc')
        today = fields.Date.context_today(env.user)
        done = O.search_count([('facility_id', 'in', facs.ids), ('state', '=', 'delivered'),
                               ('delivered_at', '>=', '%s 00:00:00' % today)])
        pending = O.search([('facility_id', 'in', facs.ids), ('state', '=', 'await_approval')])
        stations = env['care.hosp.station'].sudo().search([('facility_id', 'in', facs.ids)])
        return _ok({
            'available': True,
            'stats': {
                'queue': len(live.filtered(lambda o: o.state != 'ready')),
                'late': len(live.filtered('is_late')),
                'ready': len(live.filtered(lambda o: o.state == 'ready')),
                'delivered_today': done,
                'awaiting_approval': len(pending),
            },
            'stations': [{'id': s.id, 'name': s.name, 'icon': s.icon or '🍳'} for s in stations],
            'orders': [self._order(o) for o in live],
            'approvals': [self._order(o) for o in pending],
        })

    @route(API + '/hosp/kitchen/<int:oid>/<string:act>', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def kitchen_act(self, oid, act, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        o = env['care.hosp.order'].sudo().browse(oid).exists()
        if not o or o.facility_id.id not in self._facilities(env).ids:
            return _err('الطلب غير موجود', 404)
        try:
            {'accept': o.action_accept, 'preparing': o.action_preparing,
             'ready': o.action_ready, 'deliver': o.action_deliver,
             'approve': o.action_approve, 'reject': o.action_reject}.get(
                act, lambda: (_ for _ in ()).throw(ValueError('إجراء غير معروف')))()
        except Exception as e:
            return _err(str(getattr(e, 'args', [e])[0] if getattr(e, 'args', None) else e), 422)
        return _ok(self._order(o))

    @route(API + '/hosp/place', type='http', auth='public', methods=['POST'],
           csrf=False, cors='*')
    def hosp_set_place(self, **kw):
        """Set my serving place — by location id, by scanned code, or by name."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        b = _body()
        try:
            env.user.hosp_set_place(
                location_id=int(b['location_id']) if b.get('location_id') else None,
                room_label=b.get('room_label'),
                code=b.get('code'))
        except Exception as e:
            return _err(str(e) or 'تعذّر الحفظ', 422)
        return _ok({'location': env.user.hosp_location_id.name or None,
                    'room_label': env.user.hosp_room_label or None})

    # ---- pantry: what is left, in servings, and how to refill it -----------
    @route(API + '/hosp/stock', type='http', auth='public', methods=['GET'],
           csrf=False, cors='*')
    def hosp_stock(self, **kw):
        """The pantry as a storekeeper reads it.

        Grams are what the scale says; servings are what the decision needs.
        Both travel, plus days of cover, so "order more coffee" stops being a
        guess.
        """
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        S = env['care.hosp.supply'].sudo()
        P = env['care.hosp.purchase'].sudo()
        uom = dict(S._fields['uom_name'].selection)
        cat = dict(S._fields['category'].selection)
        sups = S.search([('active', '=', True)])
        return _ok({
            'supplies': [{
                'id': s.id, 'name': s.name, 'code': s.code,
                'category': s.category, 'category_label': cat.get(s.category, ''),
                'uom': s.uom_name, 'uom_label': uom.get(s.uom_name, ''),
                'pack_name': s.pack_name, 'pack_size': s.pack_size,
                'on_hand': s.on_hand, 'packs': round(s.packs_on_hand, 2),
                'min_qty': s.min_qty, 'low': s.low_stock,
                'servings_left': round(s.servings_left),
                'per_serving': s.per_serving_hint,
                'daily_use': round(s.daily_use, 2),
                'days_cover': round(s.days_cover, 1),
                'unit_cost': s.unit_cost, 'value': round(s.stock_value, 3),
                'supplier_type': s.supplier_type,
                'supplier': s.partner_id.name or None,
                'used_in': [{'item': r.item_id.name,
                             'qty': r.qty_per_serving,
                             'per_pack': round(r.servings_per_pack),
                             'option': r.option_id.name or None}
                            for r in s.recipe_ids],
            } for s in sups],
            'totals': {
                'value': round(sum(sups.mapped('stock_value')), 3),
                'low': len(sups.filtered('low_stock')),
                'urgent': len([s for s in sups if s.days_cover and s.days_cover < 7]),
            },
            'purchases': [{
                'id': p.id, 'name': p.name, 'date': str(p.date),
                'source': p.source, 'state': p.state,
                'supplier': p.partner_id.name or 'CARE',
                'lines': len(p.line_ids), 'total': round(p.total_cost, 3),
            } for p in P.search([], order='date desc, id desc', limit=40)],
        })

    @route(API + '/hosp/purchase/create', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def hosp_purchase_create(self, **kw):
        """Order supplies — from CARE's own store or an outside vendor."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        b = _body()
        lines = b.get('lines') or []
        if not lines:
            return _err('أضف صنفًا واحدًا على الأقل', 422)
        fac = env['care.cafm.facility'].sudo().browse(
            int(b['facility_id'])) if b.get('facility_id') else \
            env['care.hosp.supply'].sudo().search([], limit=1).facility_id
        if not fac:
            return _err('المرفق مطلوب', 422)
        try:
            p = env['care.hosp.purchase'].sudo().create({
                'facility_id': fac.id,
                'source': b.get('source') or 'care',
                'partner_id': int(b['partner_id']) if b.get('partner_id') else False,
                'reference': b.get('reference') or False,
                'note': b.get('note') or False,
                'line_ids': [(0, 0, {
                    'supply_id': int(l['supply_id']),
                    'quantity': float(l.get('quantity') or 1),
                    'by_pack': l.get('by_pack', True),
                    'unit_cost': float(l.get('unit_cost') or 0) or False,
                }) for l in lines],
            })
        except Exception as e:
            return _err(str(e) or 'تعذّر الحفظ', 422)
        return _ok({'id': p.id, 'name': p.name, 'total': round(p.total_cost, 3)})

    @route(API + '/hosp/purchase/<int:pid>/<string:act>', type='http',
           auth='public', methods=['POST'], csrf=False, cors='*')
    def hosp_purchase_act(self, pid, act, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        p = env['care.hosp.purchase'].sudo().browse(pid).exists()
        if not p:
            return _err('غير موجود', 404)
        # scope: purchase must belong to a facility the caller manages — these
        # actions move money (unit_cost) and pantry stock.
        if p.facility_id.id not in self._facilities(env).ids:
            return _err('غير مصرّح', 403)
        fn = {'submit': p.action_submit, 'approve': p.action_approve,
              'receive': p.action_receive, 'cancel': p.action_cancel}.get(act)
        if not fn:
            return _err('إجراء غير معروف', 400)
        try:
            fn()
        except Exception as e:
            return _err(str(e) or 'تعذّر التنفيذ', 422)
        return _ok({'state': p.state})

    # ---- suppliers and the supply catalogue --------------------------------
    @route(API + '/hosp/suppliers', type='http', auth='public', methods=['GET'],
           csrf=False, cors='*')
    def hosp_suppliers(self, **kw):
        """Who we buy from, and what a purchase line may point at."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        P = env['res.partner'].sudo()
        parts = P.search([('supplier_rank', '>', 0)], limit=200) or \
            P.search([('is_company', '=', True)], limit=200)
        S = env['care.hosp.supply'].sudo()
        cat = dict(S._fields['category'].selection)
        uom = dict(S._fields['uom_name'].selection)
        return _ok({
            'suppliers': [{'id': p.id, 'name': p.name, 'phone': p.phone or None,
                           'email': p.email or None} for p in parts],
            'categories': [{'code': c, 'label': l} for c, l in cat.items()],
            'uoms': [{'code': c, 'label': l} for c, l in uom.items()],
        })

    @route(API + '/hosp/supply/save', type='http', auth='public', methods=['POST'],
           csrf=False, cors='*')
    def hosp_supply_save(self, **kw):
        """Register a consumable, or correct one.

        Materials belong in the catalogue, not typed fresh into every purchase
        — otherwise the same coffee arrives under four spellings and no
        balance can ever be trusted.
        """
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        b = _body()
        name = (b.get('name') or '').strip()
        if not name:
            return _err('اسم المستهلك مطلوب', 422)
        vals = {
            'name': name,
            'code': b.get('code') or False,
            'category': b.get('category') or 'other',
            'uom_name': b.get('uom_name') or 'g',
            'pack_name': b.get('pack_name') or 'كيس',
            'pack_size': float(b.get('pack_size') or 1000),
            'min_qty': float(b.get('min_qty') or 0),
            'unit_cost': float(b.get('unit_cost') or 0),
            'supplier_type': b.get('supplier_type') or 'care',
            'partner_id': int(b['partner_id']) if b.get('partner_id') else False,
        }
        S = env['care.hosp.supply'].sudo()
        if b.get('id'):
            rec = S.browse(int(b['id'])).exists()
            if not rec:
                return _err('غير موجود', 404)
            rec.write(vals)
        else:
            fac = env['care.cafm.facility'].sudo().browse(
                int(b['facility_id'])) if b.get('facility_id') else \
                S.search([], limit=1).facility_id
            vals['facility_id'] = fac.id or False
            rec = S.create(vals)
            if b.get('opening_qty'):
                rec._apply(float(b['opening_qty']), 'receipt',
                           note=_('رصيد افتتاحي'))
        return _ok({'id': rec.id, 'name': rec.name})

    @route(API + '/hosp/purchase/<int:pid>', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def hosp_purchase_detail(self, pid, **kw):
        """One purchase, with its lines — a list you cannot open is a receipt."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        p = env['care.hosp.purchase'].sudo().browse(pid).exists()
        if not p:
            return _err('غير موجود', 404)
        uom = dict(env['care.hosp.supply']._fields['uom_name'].selection)
        return _ok({
            'id': p.id, 'name': p.name, 'date': str(p.date),
            'source': p.source, 'state': p.state,
            'supplier': p.partner_id.name or 'CARE',
            'reference': p.reference or None, 'note': p.note or None,
            'total': round(p.total_cost, 3),
            'facility': p.facility_id.name or None,
            'lines': [{
                'id': l.id, 'supply': l.supply_id.name,
                'quantity': l.quantity, 'by_pack': l.by_pack,
                'unit': l.uom_label,
                'base_qty': l.base_qty,
                'uom': uom.get(l.supply_id.uom_name, ''),
                'unit_cost': l.unit_cost or l.supply_id.unit_cost,
                'subtotal': round(l.subtotal, 3),
            } for l in p.line_ids],
        })
