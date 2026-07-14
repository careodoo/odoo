# -*- coding: utf-8 -*-
"""Client-facing INTERNAL INVENTORY endpoints — stores, stock balances, low
stock, movements, and a scan-to-issue flow (worker scans a product barcode to
consume it from a store to a facility/location). Scoped to the client's
facilities."""
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _body, API


def _sel(Model, field):
    try:
        return dict(Model.fields_get([field])[field].get('selection') or [])
    except Exception:
        return {}


def _d(v):
    return v and str(v) or None


class InventoryClientApi(Controller):

    def _facilities(self, env):
        if env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system'):
            return env['care.cafm.facility'].sudo().search([])
        p = env.user.partner_id
        pids = {p.id}
        if p.commercial_partner_id:
            pids.add(p.commercial_partner_id.id)
            pids.update(env['res.partner'].sudo().search(
                [('commercial_partner_id', '=', p.commercial_partner_id.id)]).ids)
        return env['care.cafm.facility'].sudo().search([('partner_id', 'in', list(pids))])

    def _fac_ids(self, env):
        facs = self._facilities(env)
        fid = request.httprequest.args.get('facility_id')
        if fid and fid.isdigit() and int(fid) in facs.ids:
            return [int(fid)]
        return facs.ids

    def _stores(self, env):
        return env['care.cafm.store'].sudo().search([('facility_id', 'in', self._fac_ids(env))])

    def _guard(self, env):
        if 'care.cafm.store' not in env:
            return _err('المخزون غير مفعّل', 404)
        return None

    # ---- summary ----------------------------------------------------------
    @route(API + '/client/inv/summary', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def inv_summary(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.cafm.store' not in env:
            return _ok({'available': False})
        stores = self._stores(env)
        items = env['care.cafm.stock.item'].sudo().search([('store_id', 'in', stores.ids)]) if stores else env['care.cafm.stock.item'].sudo().browse()
        from odoo import fields as F
        first = F.Date.context_today(env['care.cafm.store']).replace(day=1)
        moves_month = env['care.cafm.stock.move'].sudo().search_count(
            [('store_id', 'in', stores.ids), ('date', '>=', str(first))]) if stores else 0
        return _ok({
            'available': True,
            'stores': len(stores),
            'items': len(items),
            'low_stock': len(items.filtered('low_stock')),
            'stock_value': round(sum(items.mapped('stock_value')), 2),
            'moves_month': moves_month,
        })

    # ---- stores -----------------------------------------------------------
    @route(API + '/client/inv/stores', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def inv_stores(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        M = env['care.cafm.store'].sudo()
        st = _sel(M, 'store_type')
        return _ok([{
            'id': s.id, 'name': s.name, 'code': s.code or None,
            'type': st.get(s.store_type, s.store_type or ''),
            'facility': s.facility_id.name or None, 'keeper': s.keeper_id.name or None,
            'item_count': s.item_count, 'low_count': s.low_count,
            'stock_value': round(s.stock_value, 2),
        } for s in self._stores(env)])

    # ---- stock items (balances) ------------------------------------------
    @route(API + '/client/inv/items', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def inv_items(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        dom = [('store_id', 'in', self._stores(env).ids)]
        sid = request.httprequest.args.get('store_id')
        if sid and sid.isdigit():
            dom.append(('store_id', '=', int(sid)))
        if kw.get('low') in ('1', 'true'):
            dom.append(('low_stock', '=', True))
        recs = env['care.cafm.stock.item'].sudo().search(dom, order='low_stock desc, product_id')
        return _ok([{
            'id': it.id, 'product': it.product_id.display_name, 'product_id': it.product_id.id,
            'store': it.store_id.name or None, 'store_id': it.store_id.id,
            'barcode': it.barcode or it.default_code or None,
            'on_hand': it.on_hand, 'uom': it.uom_name or None,
            'min_qty': it.min_qty, 'max_qty': it.max_qty,
            'low_stock': it.low_stock, 'to_reorder': it.to_reorder,
            'unit_cost': it.unit_cost, 'stock_value': round(it.stock_value, 2),
            'last_move': _d(it.last_move_date),
            'image': '/api/v1/product/%s/image' % it.product_id.id,
        } for it in recs])

    # ---- movements --------------------------------------------------------
    @route(API + '/client/inv/moves', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def inv_moves(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        M = env['care.cafm.stock.move'].sudo()
        mt = _sel(M, 'move_type')
        dom = [('store_id', 'in', self._stores(env).ids)]
        if kw.get('type'):
            dom.append(('move_type', '=', kw['type']))
        recs = M.search(dom, order='date desc, id desc', limit=200)
        return _ok([{
            'id': m.id, 'name': m.name, 'type': mt.get(m.move_type, m.move_type or ''),
            'type_raw': m.move_type, 'product': m.product_id.display_name,
            'store': m.store_id.name or None, 'quantity': m.quantity, 'uom': m.uom_name or None,
            'facility': m.facility_id.name or None, 'location': m.location_id.name or None,
            'employee': m.employee_id.name or None, 'date': _d(m.date),
            'total_cost': m.total_cost, 'state': m.state, 'note': m.note or None,
        } for m in recs])

    # ---- scan-to-issue (worker consumes a product) ------------------------
    @route(API + '/client/inv/scan-issue', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def inv_scan_issue(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        b = _body()
        store_id = b.get('store_id')
        barcode = (b.get('barcode') or '').strip()
        if not store_id or not barcode:
            return _err('المخزن والباركود مطلوبان', 422)
        store = env['care.cafm.store'].sudo().browse(int(store_id)).exists()
        if not store or store.facility_id.id not in self._fac_ids(env):
            return _err('المخزن غير موجود', 404)
        try:
            qty = float(b.get('quantity') or 1.0)
            move = env['care.cafm.stock.move'].sudo().scan_issue(
                store.id, barcode, quantity=qty,
                facility_id=b.get('facility_id') or store.facility_id.id,
                location_id=b.get('location_id') or None,
            )
        except Exception as e:
            return _err(str(e), 422)
        it = move.item_id
        return _ok({
            'id': move.id, 'name': move.name, 'product': move.product_id.display_name,
            'quantity': move.quantity, 'on_hand': it.on_hand if it else None,
            'low_stock': it.low_stock if it else False,
        })

    # ---- receive stock (goods-in from a CARE order) -----------------------
    @route(API + '/client/inv/receive', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def inv_receive(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        b = _body()
        store = env['care.cafm.store'].sudo().browse(int(b['store_id'])).exists() if b.get('store_id') else None
        if not store or store.facility_id.id not in self._fac_ids(env):
            return _err('المخزن غير موجود', 404)
        barcode = (b.get('barcode') or '').strip()
        p = env['product.product'].sudo().search(
            ['|', ('barcode', '=', barcode), ('default_code', '=', barcode)], limit=1) if barcode else None
        if not p and b.get('product_id'):
            p = env['product.product'].sudo().browse(int(b['product_id'])).exists()
        if not p:
            return _err('المنتج غير موجود', 404)
        try:
            move = env['care.cafm.stock.move'].sudo().create({
                'move_type': 'receipt', 'store_id': store.id, 'product_id': p.id,
                'quantity': float(b.get('quantity') or 1.0), 'unit_cost': float(b.get('unit_cost') or 0.0),
                'order_ref': b.get('order_ref') or None, 'scan_code': barcode or None,
            })
            move.action_done()
        except Exception as e:
            return _err(str(e), 422)
        return _ok({'id': move.id, 'name': move.name, 'on_hand': move.item_id.on_hand if move.item_id else None})
