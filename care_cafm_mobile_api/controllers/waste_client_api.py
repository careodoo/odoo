# -*- coding: utf-8 -*-
"""Client-facing WASTE-TRANSFER & TREATMENT endpoints — surfaces the
service_order module (collection orders → trips → treatment centers) as a CAFM
service, scoped to the client's partner via service.project.contact_id.
Read + create a new collection order, mirroring the existing portal form."""
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _body, API


def _sel(Model, field):
    try:
        return dict(Model.fields_get([field])[field].get('selection') or [])
    except Exception:
        return {}


def _d(v):
    return v and str(v) or None


class WasteClientApi(Controller):

    def _partner_ids(self, env):
        p = env.user.partner_id
        ids = {p.id}
        if p.commercial_partner_id:
            ids.add(p.commercial_partner_id.id)
            ids.update(env['res.partner'].sudo().search(
                [('commercial_partner_id', '=', p.commercial_partner_id.id)]).ids)
        return list(ids)

    def _is_mgr(self, env):
        return env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system')

    def _projects(self, env):
        """service.project records belonging to this client."""
        Proj = env['service.project'].sudo()
        if self._is_mgr(env):
            return Proj.search([])
        return Proj.search([('contact_id', 'in', self._partner_ids(env))])

    def _order_domain(self, env):
        return [('project_id', 'in', self._projects(env).ids)]

    def _guard(self, env):
        if 'service.order' not in env:
            return _err('خدمة نقل ومعالجة النفايات غير مفعّلة', 404)
        return None

    # ---- summary ----------------------------------------------------------
    @route(API + '/client/waste/summary', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def waste_summary(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'service.order' not in env:
            return _ok({'available': False})
        SO = env['service.order'].sudo()
        dom = self._order_domain(env)
        open_states = ('draft', 'scheduled', 'pickuped', 'arrived', 'processing')
        return _ok({
            'available': True,
            'orders': SO.search_count(dom),
            'open': SO.search_count(dom + [('states', 'in', open_states)]),
            'completed': SO.search_count(dom + [('states', 'in', ('completed', 'delivered'))]),
            'trips': env['service.trip'].sudo().search_count(
                [('project_id', 'in', self._projects(env).ids)]) if 'service.trip' in env else 0,
            'centers': env['service.center'].sudo().search_count([]) if 'service.center' in env else 0,
        })

    # ---- collection orders ------------------------------------------------
    @route(API + '/client/waste/orders', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def waste_orders(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        SO = env['service.order'].sudo()
        st = _sel(SO, 'states')
        dom = self._order_domain(env)
        if kw.get('state'):
            dom.append(('states', '=', kw['state']))
        recs = SO.search(dom, order='id desc', limit=200)
        return _ok([{
            'id': o.id, 'serial': o.serial or o.display_name,
            'project': o.project_id.name or None,
            'pickup': o.pickup_location_id.name if 'pickup_location_id' in o._fields and o.pickup_location_id else None,
            'type': o.type_id.name if 'type_id' in o._fields and o.type_id else None,
            'order_date': _d(getattr(o, 'order_datetime', False)),
            'request_date': _d(getattr(o, 'request_datetime', False)),
            'items': [{'item': l.item_id.name if l.item_id else None,
                       'qty': l.quantity} for l in o.order_line_ids],
            'trip': o.trip_id.sequence if 'trip_id' in o._fields and o.trip_id else None,
            'state': o.states, 'state_label': st.get(o.states, o.states or ''),
        } for o in recs])

    # ---- trips ------------------------------------------------------------
    @route(API + '/client/waste/trips', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def waste_trips(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        if 'service.trip' not in env:
            return _ok([])
        T = env['service.trip'].sudo()
        st = _sel(T, 'states')
        recs = T.search([('project_id', 'in', self._projects(env).ids)], order='id desc', limit=200)
        return _ok([{
            'id': t.id, 'sequence': t.sequence or t.display_name,
            'pickup': t.pickup_location_id.name if t.pickup_location_id else None,
            'center': t.center_id.name if t.center_id else None,
            'date': _d(getattr(t, 'trip_date', False)),
            'pickuped': _d(getattr(t, 'pickuped_datetime', False)),
            'total_weight': getattr(t, 'total_weight', 0.0),
            'total_quantity': getattr(t, 'total_quantity', 0.0),
            'team': t.team_id.name if 'team_id' in t._fields and t.team_id else None,
            'state': t.states, 'state_label': st.get(t.states, t.states or ''),
        } for t in recs])

    # ---- treatment centers ------------------------------------------------
    @route(API + '/client/waste/centers', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def waste_centers(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        if 'service.center' not in env:
            return _ok([])
        recs = env['service.center'].sudo().search([])
        return _ok([{'id': c.id, 'name': c.name} for c in recs])

    # ---- create a collection order ----------------------------------------
    @route(API + '/client/waste/order/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def waste_order_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        b = _body()
        projs = self._projects(env)
        pid = int(b['project_id']) if b.get('project_id') else (projs[:1].id if projs else None)
        if not pid or pid not in projs.ids:
            return _err('المشروع مطلوب', 422)
        vals = {'project_id': pid}
        if b.get('pickup_location_id'):
            vals['pickup_location_id'] = int(b['pickup_location_id'])
        if b.get('type_id'):
            vals['type_id'] = int(b['type_id'])
        lines = []
        for it in (b.get('items') or []):
            if it.get('item_id'):
                lines.append((0, 0, {'item_id': int(it['item_id']), 'quantity': float(it.get('quantity') or 1.0)}))
        if lines:
            vals['order_line_ids'] = lines
        try:
            o = env['service.order'].sudo().create(vals)
        except Exception as e:
            return _err(str(e), 422)
        return _ok({'id': o.id, 'serial': o.serial or o.display_name, 'state': o.states})

    # ---- form options (pickup locations / types / items) ------------------
    @route(API + '/client/waste/options', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def waste_options(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        projs = self._projects(env)
        Pick = env['service.pickup.location'].sudo()
        picks = Pick.search([('project_id', 'in', projs.ids)]) if 'service.pickup.location' in env else Pick.browse()
        items = env['service.item'].sudo().search([]) if 'service.item' in env else None
        return _ok({
            'projects': [{'id': p.id, 'name': p.name} for p in projs],
            'pickups': [{'id': p.id, 'name': p.name, 'project_id': p.project_id.id} for p in picks],
            'items': [{'id': i.id, 'name': i.name} for i in items] if items is not None else [],
        })
