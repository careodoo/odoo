# -*- coding: utf-8 -*-
"""Client-facing WASTE-TRANSFER & TREATMENT endpoints — surfaces the
service_order module (collection orders → trips → treatment centers) as a CAFM
service, scoped to the client's partner via service.project.contact_id.
Read + create a new collection order, mirroring the existing portal form."""
import base64

from odoo import fields
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _body, _abs, API

_PLACEHOLDER = ('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk'
                'YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')


def _wm(env):
    """Model map for the waste API. Flip system parameter
    ``care.waste.source`` to ``cafm`` (after migrating data) to serve the app
    from the new independent CAFM waste module instead of legacy service_order.
    Field names are identical across both, so only the model names change."""
    src = env['ir.config_parameter'].sudo().get_param('care.waste.source', 'legacy')
    if src == 'cafm' and 'cafm.waste.order' in env:
        return {'order': 'cafm.waste.order', 'trip': 'cafm.waste.trip',
                'center': 'cafm.waste.center', 'pickup': 'cafm.waste.pickup.location',
                'item': 'cafm.waste.item', 'project': 'cafm.waste.project'}
    return {'order': 'service.order', 'trip': 'service.trip',
            'center': 'service.center', 'pickup': 'service.pickup.location',
            'item': 'service.item', 'project': 'service.project'}


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
        # include CAFM clients this user belongs to (portal sub-users)
        if 'care.cafm.client' in env:
            clients = env['care.cafm.client'].sudo().search([('user_ids', 'in', [env.user.id])])
            for cp in clients.mapped('partner_id'):
                ids.add(cp.id)
                ids.update(env['res.partner'].sudo().search(
                    [('commercial_partner_id', '=', cp.id)]).ids)
        return list(ids)

    def _is_mgr(self, env):
        return env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system')

    def _projects(self, env):
        """service.project records belonging to this client."""
        Proj = env[_wm(env)['project']].sudo()
        if self._is_mgr(env):
            return Proj.search([])
        return Proj.search([('contact_id', 'in', self._partner_ids(env))])

    def _order_domain(self, env):
        return [('project_id', 'in', self._projects(env).ids)]

    def _guard(self, env):
        if _wm(env)['order'] not in env:
            return _err('خدمة نقل ومعالجة النفايات غير مفعّلة', 404)
        return None

    # ---- summary ----------------------------------------------------------
    @route(API + '/client/waste/summary', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def waste_summary(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if _wm(env)['order'] not in env:
            return _ok({'available': False})
        SO = env[_wm(env)['order']].sudo()
        dom = self._order_domain(env)
        open_states = ('draft', 'scheduled', 'pickuped', 'arrived', 'processing')
        is_cafm = _wm(env)['order'] == 'cafm.waste.order'
        return _ok({
            'available': True,
            'orders': SO.search_count(dom),
            'open': SO.search_count(dom + [('states', 'in', open_states)]),
            'completed': SO.search_count(dom + [('states', 'in', ('completed', 'delivered'))]),
            'trips': env[_wm(env)['trip']].sudo().search_count(
                [('project_id', 'in', self._projects(env).ids)]) if _wm(env)['trip'] in env else 0,
            'centers': env[_wm(env)['center']].sudo().search_count([]) if _wm(env)['center'] in env else 0,
            # source-aware web-portal paths the app opens via SSO WebView
            'portal_path': '/waste/orders' if is_cafm else '/service_orders',
            'create_path': '/waste/order/create' if is_cafm else '/service_order/create',
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
        SO = env[_wm(env)['order']].sudo()
        st = _sel(SO, 'states')
        dom = self._order_domain(env)
        if kw.get('state'):
            dom.append(('states', '=', kw['state']))
        if kw.get('q'):
            q = kw['q']
            dom += ['|', '|', ('serial', 'ilike', q), ('project_id.name', 'ilike', q),
                    ('pickup_location_id.name', 'ilike', q)]
        if kw.get('date_from'):
            dom.append(('request_datetime', '>=', '%s 00:00:00' % kw['date_from']))
        if kw.get('date_to'):
            dom.append(('request_datetime', '<=', '%s 23:59:59' % kw['date_to']))
        order_by = 'serial desc' if _wm(env)['order'] == 'cafm.waste.order' else 'id desc'
        recs = SO.search(dom, order=order_by, limit=200)
        def g_(o, f):
            return getattr(o, f) if f in o._fields else False
        def lines(o):
            # items live on the order, or fall back to the trip (legacy layout)
            return o.order_line_ids or (o.trip_id.trip_line_ids if ('trip_id' in o._fields and o.trip_id) else o.order_line_ids)
        return _ok([{
            'id': o.id, 'serial': o.serial or o.display_name,
            'project': o.project_id.name or None,
            'pickup': o.pickup_location_id.name if 'pickup_location_id' in o._fields and o.pickup_location_id else None,
            'type': o.type_id.name if 'type_id' in o._fields and o.type_id else None,
            'order_date': _d(getattr(o, 'order_datetime', False)),
            'request_date': _d(getattr(o, 'request_datetime', False)),
            'items': [self._item_dict(l) for l in lines(o)],
            'items_count': len(lines(o)),
            'qty_total': sum((l.quantity or 0) for l in lines(o)),
            'weight_total': round(sum((l.quantity or 0) * (getattr(l, 'weight', 0) or 0) for l in lines(o)), 1),
            'trip': o.trip_id.sequence if 'trip_id' in o._fields and o.trip_id else None,
            'ops_manager': g_(o, 'ops_manager_id').name if g_(o, 'ops_manager_id') else None,
            'driver': g_(o, 'driver_id').name if g_(o, 'driver_id') else None,
            'receiver': g_(o, 'receiver_id').name if g_(o, 'receiver_id') else None,
            'final_weight': g_(o, 'final_weight') or 0.0,
            'final_note': g_(o, 'final_note') or None,
            'notes': g_(o, 'notes') or None,
            'proof': _abs('/api/v1/waste/proof/%s' % o.id) if g_(o, 'proof_image') else None,
            'media': self._media_list(g_(o, 'media_ids')),
            'report_path': ('/waste/order/%s/report' if _wm(env)['order'] == 'cafm.waste.order' else '/service_order/%s/') % o.id,
            'state': o.states, 'state_label': st.get(o.states, o.states or ''),
        } for o in recs])

    def _media_list(self, attachments):
        if not attachments:
            return []
        out = []
        for a in attachments:
            mt = a.mimetype or ''
            out.append({'id': a.id, 'url': _abs('/api/v1/waste/media/%s' % a.id),
                        'mimetype': mt, 'is_video': mt.startswith('video'),
                        'name': a.name})
        return out

    @route(API + '/waste/media/<int:aid>', type='http', auth='public', csrf=False, cors='*')
    def waste_media(self, aid, **kw):
        a = request.env['ir.attachment'].sudo().browse(int(aid)).exists()
        if not a or a.res_model not in ('cafm.waste.order', 'cafm.waste.trip'):
            return request.not_found()
        raw = base64.b64decode(a.datas) if a.datas else b''
        return request.make_response(raw, headers=[
            ('Content-Type', a.mimetype or 'application/octet-stream'),
            ('Content-Length', str(len(raw))), ('Cache-Control', 'public, max-age=3600')])

    def _item_dict(self, line):
        it = line.item_id
        return {
            'item': it.name if it else None,
            'item_id': it.id if it else None,
            'qty': line.quantity,
            'uom': it.uom_id.name if (it and 'uom_id' in it._fields and it.uom_id) else None,
            'image': _abs('/api/v1/waste/item/%s/image' % it.id) if (it and getattr(it, 'image', False)) else None,
        }

    # public images (served via sudo so <img> renders without a token) ---------
    def _img_response(self, model, rid, field):
        rec = request.env[model].sudo().browse(int(rid)).exists()
        data = rec[field] if rec and field in rec._fields else None
        raw = base64.b64decode(data) if data else base64.b64decode(_PLACEHOLDER)
        return request.make_response(raw, headers=[
            ('Content-Type', 'image/png'), ('Content-Length', str(len(raw))),
            ('Cache-Control', 'public, max-age=3600')])

    @route(API + '/waste/item/<int:iid>/image', type='http', auth='public', csrf=False, cors='*')
    def waste_item_image(self, iid, **kw):
        return self._img_response(_wm(request.env)['item'], iid, 'image')

    @route(API + '/waste/proof/<int:oid>', type='http', auth='public', csrf=False, cors='*')
    def waste_proof_image(self, oid, **kw):
        return self._img_response(_wm(request.env)['order'], oid, 'proof_image')

    # ---- trips ------------------------------------------------------------
    @route(API + '/client/waste/trips', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def waste_trips(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        if _wm(env)['trip'] not in env:
            return _ok([])
        T = env[_wm(env)['trip']].sudo()
        st = _sel(T, 'states')
        torder = 'sequence desc' if _wm(env)['trip'] == 'cafm.waste.trip' else 'id desc'
        tdom = [('project_id', 'in', self._projects(env).ids)]
        if kw.get('state'):
            tdom.append(('states', '=', kw['state']))
        if kw.get('q'):
            tdom += ['|', ('sequence', 'ilike', kw['q']), ('center_id.name', 'ilike', kw['q'])]
        if kw.get('date_from'):
            tdom.append(('trip_date', '>=', kw['date_from']))
        if kw.get('date_to'):
            tdom.append(('trip_date', '<=', kw['date_to']))
        recs = T.search(tdom, order=torder, limit=200)

        def dloc(t):
            if 'driver_lat' in t._fields and (t.driver_lat or t.driver_lng):
                return {'lat': t.driver_lat, 'lng': t.driver_lng, 'time': _d(t.driver_loc_time),
                        'driver': t.driver_id.name if ('driver_id' in t._fields and t.driver_id) else None}
            return None
        return _ok([{
            'id': t.id, 'sequence': t.sequence or t.display_name,
            'pickup': t.pickup_location_id.name if t.pickup_location_id else None,
            'center': t.center_id.name if t.center_id else None,
            'date': _d(getattr(t, 'trip_date', False)),
            'pickuped': _d(getattr(t, 'pickuped_datetime', False)),
            # total weight = Σ(quantity × piece weight) — NOT the bare sum of piece weights
            'total_weight': round(sum((getattr(l, 'quantity', 0) or 0) * (getattr(l, 'weight', 0) or 0)
                                      for l in (t.trip_line_ids if 'trip_line_ids' in t._fields else [])), 1),
            'total_quantity': round(sum((getattr(l, 'quantity', 0) or 0)
                                        for l in (t.trip_line_ids if 'trip_line_ids' in t._fields else [])), 1),
            'team': t.team_id.name if 'team_id' in t._fields and t.team_id else None,
            'driver': t.driver_id.name if ('driver_id' in t._fields and t.driver_id) else None,
            'location': dloc(t),
            'media': self._media_list(t.media_ids if 'media_ids' in t._fields else None),
            'items': [{'item': l.item_id.name if ('item_id' in l._fields and l.item_id) else None,
                       'qty': getattr(l, 'quantity', 0), 'weight': getattr(l, 'weight', 0),
                       'image': _abs('/api/v1/waste/item/%s/image' % l.item_id.id) if ('item_id' in l._fields and l.item_id and getattr(l.item_id, 'image', False)) else None}
                      for l in t.trip_line_ids] if 'trip_line_ids' in t._fields else [],
            'order_count': len(t.order_ids) if 'order_ids' in t._fields else (1 if ('order_id' in t._fields and t.order_id) else 0),
            'report_path': ('/waste/trip/%s/report' % t.id) if _wm(env)['trip'] == 'cafm.waste.trip' else None,
            'state': t.states, 'state_label': st.get(t.states, t.states or ''),
        } for t in recs])

    # ---- treatment-center receiver: incoming orders + confirm -------------
    @route(API + '/waste/receiver/orders', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def waste_receiver_orders(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'cafm.waste.order' not in env:
            return _ok([])
        O = env['cafm.waste.order'].sudo()
        dom = [('receiver_id', '=', env.user.id)]
        if not kw.get('all'):
            dom.append(('states', 'in', ('pickuped', 'arrived', 'processing')))
        recs = O.search(dom, order='serial desc', limit=100)
        st = _sel(O, 'states')
        return _ok([{
            'id': o.id, 'serial': o.serial, 'project': o.project_id.name or None,
            'pickup': o.pickup_location_id.name if o.pickup_location_id else None,
            'center': o.trip_id.center_id.name if (o.trip_id and o.trip_id.center_id) else None,
            'final_weight': o.final_weight, 'final_note': o.final_note or None,
            'items': [self._item_dict(l) for l in (o.order_line_ids or (o.trip_id.trip_line_ids if o.trip_id else o.order_line_ids))],
            'media_count': len(o.media_ids),
            'state': o.states, 'state_label': st.get(o.states, o.states or ''),
        } for o in recs])

    @route(API + '/waste/order/<int:oid>/receive', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def waste_order_receive(self, oid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'cafm.waste.order' not in env:
            return _err('غير متاح', 404)
        o = env['cafm.waste.order'].sudo().browse(int(oid)).exists()
        if not o:
            return _err('غير موجود', 404)
        b = _body()
        vals = {}
        if b.get('final_weight') is not None:
            vals['final_weight'] = float(b['final_weight'] or 0)
        if b.get('final_note') is not None:
            vals['final_note'] = b['final_note']
        vals['receiver_id'] = env.user.id
        o.write(vals)
        # update item types/quantities on the order (what the center actually received)
        if b.get('items') is not None:
            o.order_line_ids.unlink()
            o.write({'order_line_ids': [(0, 0, {'item_id': int(it['item_id']), 'quantity': float(it.get('quantity') or 0)})
                                        for it in b['items'] if it.get('item_id')]})
        # attach uploaded media (base64 images/videos) to the order + its trip
        for m in (b.get('media') or []):
            data = m.get('data') or ''
            if ',' in data:
                data = data.split(',', 1)[1]
            if not data:
                continue
            att = env['ir.attachment'].sudo().create({
                'name': m.get('name') or 'media', 'datas': data,
                'mimetype': m.get('mimetype') or 'image/jpeg',
                'res_model': 'cafm.waste.order', 'res_id': o.id})
            o.write({'media_ids': [(4, att.id)]})
            if o.trip_id:
                o.trip_id.write({'media_ids': [(4, att.id)]})
        # confirm completion → advance state
        act = b.get('confirm')
        if act == 'delivered':
            o.action_to_delivered()
        elif act == 'completed':
            o.action_to_completed()
        elif act == 'processing':
            o.action_to_processing()
        return _ok({'id': o.id, 'state': o.states, 'media_count': len(o.media_ids)})

    # ---- driver: my assigned trips ----------------------------------------
    @route(API + '/waste/driver/trips', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def waste_driver_trips(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'cafm.waste.trip' not in env:
            return _ok([])
        T = env['cafm.waste.trip'].sudo()
        dom = [('driver_id', '=', env.user.id)]
        if not kw.get('all'):
            dom.append(('states', 'in', ('scheduled', 'pickuped', 'arrived', 'processing')))
        recs = T.search(dom, order='sequence desc', limit=100)
        st = _sel(T, 'states')
        return _ok([{
            'id': t.id, 'sequence': t.sequence,
            'project': t.project_id.name or None,
            'pickup': t.pickup_location_id.name if t.pickup_location_id else None,
            'center': t.center_id.name if t.center_id else None,
            'date': _d(t.trip_date),
            'total_quantity': t.total_quantity, 'total_qty_weight': t.total_qty_weight,
            'sharing': bool(t.driver_lat or t.driver_lng),
            'state': t.states, 'state_label': st.get(t.states, t.states or ''),
        } for t in recs])

    # ---- live driver location (driver posts, client polls) ----------------
    @route(API + '/waste/trip/<int:tid>/location', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def waste_trip_set_location(self, tid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'cafm.waste.trip' not in env:
            return _err('غير متاح', 404)
        b = _body()
        t = env['cafm.waste.trip'].sudo().browse(int(tid)).exists()
        if not t:
            return _err('غير موجود', 404)
        t.write({'driver_lat': float(b.get('lat') or 0), 'driver_lng': float(b.get('lng') or 0),
                 'driver_loc_time': fields.Datetime.now(), 'driver_id': env.user.id})
        return _ok({'ok': True})

    @route(API + '/waste/trip/<int:tid>/track', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def waste_trip_track(self, tid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        t = env['cafm.waste.trip'].sudo().browse(int(tid)).exists() if 'cafm.waste.trip' in env else None
        if not t:
            return _err('غير موجود', 404)
        return _ok({'lat': t.driver_lat, 'lng': t.driver_lng, 'time': _d(t.driver_loc_time),
                    'driver': t.driver_id.name if t.driver_id else None,
                    'center': {'name': t.center_id.name} if t.center_id else None,
                    'state': t.states})

    # ---- statistics over a period (client-scoped) -------------------------
    @route(API + '/client/waste/stats', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def waste_stats(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        SO = env[_wm(env)['order']].sudo()
        dom = self._order_domain(env)
        df, dt = kw.get('date_from'), kw.get('date_to')
        if df:
            dom.append(('order_datetime', '>=', '%s 00:00:00' % df))
        if dt:
            dom.append(('order_datetime', '<=', '%s 23:59:59' % dt))
        recs = SO.search(dom)
        st = _sel(SO, 'states')
        # aggregates
        by_state, by_item, by_month = {}, {}, {}
        total_qty = total_weight = 0.0
        done_states = ('completed', 'delivered')
        completed = 0
        def elines(o):
            return o.order_line_ids or (o.trip_id.trip_line_ids if ('trip_id' in o._fields and o.trip_id) else o.order_line_ids)
        for o in recs:
            state = o.states or 'draft'
            by_state[state] = by_state.get(state, 0) + 1
            if state in done_states:
                completed += 1
            odt = getattr(o, 'order_datetime', False) or getattr(o, 'request_datetime', False)
            mk = odt.strftime('%Y-%m') if odt else '—'
            m = by_month.setdefault(mk, {'orders': 0, 'weight': 0.0, 'qty': 0.0})
            m['orders'] += 1
            for l in elines(o):
                q = l.quantity or 0
                # weight = quantity × unit (piece) weight, summed
                w = q * (getattr(l, 'weight', 0) or 0)
                total_qty += q
                total_weight += w
                m['qty'] += q
                m['weight'] += w
                nm = l.item_id.name if l.item_id else '—'
                bi = by_item.setdefault(nm, {'qty': 0.0, 'orders': 0,
                                             'image': _abs('/api/v1/waste/item/%s/image' % l.item_id.id) if (l.item_id and getattr(l.item_id, 'image', False)) else None})
                bi['qty'] += q
                bi['orders'] += 1
        top_items = sorted(([k, v] for k, v in by_item.items()), key=lambda x: -x[1]['qty'])[:8]
        months = sorted(by_month.items())
        return _ok({
            'total_orders': len(recs),
            'completed': completed,
            'open': len(recs) - completed - by_state.get('cancelled', 0),
            'cancelled': by_state.get('cancelled', 0),
            'total_weight': round(total_weight, 1),
            'total_quantity': round(total_qty, 1),
            'by_state': [{'state': k, 'label': st.get(k, k), 'count': v} for k, v in by_state.items()],
            'by_item': [{'name': k, 'qty': round(v['qty'], 1), 'orders': v['orders'], 'image': v['image']} for k, v in top_items],
            'by_month': [{'month': k, 'orders': v['orders'], 'weight': round(v['weight'], 1), 'qty': round(v['qty'], 1)} for k, v in months],
            'print_path': ('/waste/print' if _wm(env)['order'] == 'cafm.waste.order' else '/service_order/print') + '?date_from=%s&date_to=%s' % (df or '', dt or ''),
        })

    # ---- treatment centers ------------------------------------------------
    @route(API + '/client/waste/centers', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def waste_centers(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        if _wm(env)['center'] not in env:
            return _ok([])
        recs = env[_wm(env)['center']].sudo().search([])
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
        if b.get('request_datetime'):
            vals['request_datetime'] = b['request_datetime']
        if b.get('notes'):
            vals['notes'] = b['notes']
        lines = []
        for it in (b.get('items') or []):
            if it.get('item_id'):
                lines.append((0, 0, {'item_id': int(it['item_id']), 'quantity': float(it.get('quantity') or 1.0)}))
        if lines:
            vals['order_line_ids'] = lines
        try:
            o = env[_wm(env)['order']].sudo().create(vals)
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
        Pick = env[_wm(env)['pickup']].sudo()
        picks = Pick.search([('project_id', 'in', projs.ids)]) if _wm(env)['pickup'] in env else Pick.browse()
        items = env[_wm(env)['item']].sudo().search([]) if _wm(env)['item'] in env else None
        types = env['cafm.waste.type'].sudo().search([]) if 'cafm.waste.type' in env else None
        return _ok({
            'projects': [{'id': p.id, 'name': p.name} for p in projs],
            'pickups': [{'id': p.id, 'name': p.name, 'project_id': p.project_id.id} for p in picks],
            'items': [{'id': i.id, 'name': i.name} for i in items] if items is not None else [],
            'types': [{'id': t.id, 'name': t.name} for t in types] if types is not None else [],
        })
