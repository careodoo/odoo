# -*- coding: utf-8 -*-
"""Client-facing INTERNAL INVENTORY endpoints — stores, stock balances, low
stock, movements, and a scan-to-issue flow (worker scans a product barcode to
consume it from a store to a facility/location). Scoped to the client's
facilities."""
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _body, API, _person_name


def _sel(Model, field):
    try:
        return dict(Model.fields_get([field])[field].get('selection') or [])
    except Exception:
        return {}


def _d(v):
    return v and str(v) or None


class InventoryClientApi(Controller):

    def _facilities(self, env):
        Fac = env['care.cafm.facility'].sudo()
        if env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system'):
            return Fac.search([])
        p = env.user.partner_id
        pids = {p.id}
        if p.commercial_partner_id:
            pids.add(p.commercial_partner_id.id)
            pids.update(env['res.partner'].sudo().search(
                [('commercial_partner_id', '=', p.commercial_partner_id.id)]).ids)
        facs = Fac.search([('partner_id', 'in', list(pids))])
        if facs:
            return facs
        # A field worker owns no facility, but still has to draw materials for
        # the sites they actually work on — scope them to those instead.
        emp = env.user.employee_id
        ids = set()
        if emp:
            ids |= set(env['care.cafm.workorder'].sudo().search(
                [('employee_id', '=', emp.id)]).mapped('facility_id').ids)
            if 'care.cafm.team' in env:
                ids |= set(env['care.cafm.team'].sudo().search(
                    ['|', ('member_ids', 'in', [emp.id]), ('supervisor_id', '=', env.user.id)]
                ).mapped('facility_id').ids)
        return Fac.browse(list(ids))

    def _fac_ids(self, env):
        facs = self._facilities(env)
        fid = request.httprequest.args.get('facility_id')
        if fid and fid.isdigit() and int(fid) in facs.ids:
            return [int(fid)]
        return facs.ids

    def _stores(self, env):
        return env['care.cafm.store'].sudo().search([('facility_id', 'in', self._fac_ids(env))])

    # ---- destination locations (building → floor → office/bathroom) -------
    @route(API + '/client/inv/locations', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def inv_locations(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        fids = self._fac_ids(env)
        sid = request.httprequest.args.get('store_id')
        if sid and sid.isdigit():
            st = env['care.cafm.store'].sudo().browse(int(sid)).exists()
            if st and st.facility_id:
                fids = [st.facility_id.id]
        Loc = env['care.cafm.location'].sudo()
        recs = Loc.search([('facility_id', 'in', fids)], order='building_id, name')
        return _ok([{
            'id': l.id, 'name': l.name,
            'building': l.building_id.name if 'building_id' in l._fields and l.building_id else None,
            'facility': l.facility_id.name or None,
            'path': ' › '.join(x for x in [l.facility_id.name, (l.building_id.name if 'building_id' in l._fields and l.building_id else None), l.name] if x),
        } for l in recs])

    # ---- manual issue (pick product + destination) ------------------------
    @route(API + '/client/inv/issue', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def inv_issue(self, **kw):
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
        p = None
        if b.get('product_id'):
            p = env['product.product'].sudo().browse(int(b['product_id'])).exists()
        elif b.get('barcode'):
            p = env['product.product'].sudo().search(
                ['|', ('barcode', '=', b['barcode']), ('default_code', '=', b['barcode'])], limit=1)
        if not p:
            return _err('المنتج غير موجود', 404)
        # resolve the issuing employee from the logged-in user, if linked
        emp = env['hr.employee'].sudo().search([('user_id', '=', env.user.id)], limit=1)
        qty = float(b.get('quantity') or 1.0)
        # ---- the client's self-issue policy ----------------------------------
        # Managers/keepers bypass it; a field worker may only draw items the
        # client marked issuable, for their own service, within the per-issue cap.
        u = env.user
        privileged = bool(u.has_group('base.group_erp_manager') or u.has_group('base.group_system')
                          or (u.partner_id.commercial_partner_id or u.partner_id).sudo().cafm_can_add_workers)
        if not privileged:
            item = env['care.cafm.stock.item'].sudo().search(
                [('store_id', '=', store.id), ('product_id', '=', p.id)], limit=1)
            if item:
                svc_types = []
                if emp:
                    svc_types = list({w.service_type for w in env['care.cafm.workorder'].sudo().search(
                        [('employee_id', '=', emp.id)]) if w.service_type})
                ok, why = item.worker_may_issue(service_type=(svc_types[0] if svc_types else None), qty=qty)
                if not ok:
                    return _err(why, 403)
        try:
            move = env['care.cafm.stock.move'].sudo().create({
                'move_type': 'issue', 'store_id': store.id, 'product_id': p.id,
                'quantity': float(b.get('quantity') or 1.0),
                'facility_id': store.facility_id.id,
                'location_id': int(b['location_id']) if b.get('location_id') else False,
                'employee_id': (int(b['employee_id']) if b.get('employee_id') else (emp.id if emp else False)),
                'note': b.get('note') or None,
            })
            move.action_done()
        except Exception as e:
            return _err(str(e), 422)
        it = move.item_id
        return _ok({'id': move.id, 'name': move.name, 'product': p.display_name,
                    'quantity': move.quantity, 'on_hand': it.on_hand if it else None,
                    'location': move.location_id.display_name or None})

    # ---- consumption analytics (top materials / locations / employees) ----
    @route(API + '/client/inv/consumption', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def inv_consumption(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.cafm.stock.move' not in env:
            return _ok({'available': False})
        from odoo import fields as F
        period = request.httprequest.args.get('period') or 'month'
        tdy = F.Date.context_today(env['care.cafm.store'])
        if period == 'day':
            since = tdy
        elif period == 'year':
            since = tdy.replace(month=1, day=1)
        elif period == 'all':
            since = None
        else:
            since = tdy.replace(day=1)
        Move = env['care.cafm.stock.move'].sudo()
        dom = [('move_type', '=', 'issue'), ('state', '=', 'done'),
               ('facility_id', 'in', self._fac_ids(env))]
        if since:
            dom.append(('date', '>=', str(since)))
        page = max(1, int(kw.get('page') or 1))
        per = min(200, max(20, int(kw.get('per_page') or 60)))
        moves = Move.search(dom, order='date desc, id desc',
                            limit=per, offset=(page - 1) * per)

        def top(key_fn, label_fn, limit=8):
            agg = {}
            for m in moves:
                k = key_fn(m)
                if not k:
                    continue
                a = agg.setdefault(k, {'qty': 0.0, 'value': 0.0, 'label': label_fn(m)})
                a['qty'] += m.quantity
                a['value'] += m.total_cost
            rows = [{'label': v['label'], 'qty': round(v['qty'], 1), 'value': round(v['value'], 2)} for v in agg.values()]
            return sorted(rows, key=lambda r: -r['qty'])[:limit]

        def top_id(key_fn, label_fn, limit=30):
            """Same as top() but keeps the entity id so the app can drill in."""
            agg = {}
            for m in moves:
                k = key_fn(m)
                if not k:
                    continue
                a = agg.setdefault(k, {'id': k, 'qty': 0.0, 'value': 0.0, 'issues': 0, 'label': label_fn(m)})
                a['qty'] += m.quantity
                a['value'] += m.total_cost
                a['issues'] += 1
            rows = [{'id': v['id'], 'label': v['label'], 'qty': round(v['qty'], 1),
                     'value': round(v['value'], 2), 'issues': v['issues']} for v in agg.values()]
            return sorted(rows, key=lambda r: -r['qty'])[:limit]

        return _ok({
            'available': True, 'period': period,
            'total_qty': round(sum(moves.mapped('quantity')), 1),
            'total_value': round(sum(moves.mapped('total_cost')), 2),
            'issues': len(moves),
            'top_materials': top_id(lambda m: m.product_id.id, lambda m: m.product_id.display_name),
            'top_locations': top_id(lambda m: m.location_id.id, lambda m: m.location_id.display_name or '—'),
            'top_buildings': top_id(lambda m: m.building_id.id, lambda m: m.building_id.name or '—'),
            'by_facility': top_id(lambda m: m.facility_id.id, lambda m: m.facility_id.name or '—'),
            'top_employees': top_id(lambda m: m.employee_id.id, lambda m: (_person_name(m.employee_id) or '—')),
        })

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
            # sub-store structure: which main store it belongs to, and the
            # service it serves
            'is_sub': s.is_sub,
            'parent_store': s.parent_store_id.name or None,
            'parent_store_id': s.parent_store_id.id or None,
            'service': s.service_id.name or None,
            'service_id': s.service_id.id or None,
            'service_type': s.service_id.service_type or None,
            'sub_count': len(s.child_store_ids),
            'worker_issue_allowed': s.worker_issue_allowed,
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
            # the client's self-issue policy for this item
            'allow_worker_issue': it.allow_worker_issue,
            'allowed_services': it.allowed_service_ids.mapped('name'),
            'allowed_service_ids': it.allowed_service_ids.ids,
            'max_issue_qty': it.max_issue_qty,
        } for it in recs])

    # ---- the client's material policy (client / admin only) ---------------
    def _may_set_policy(self, env):
        u = env.user
        if u.has_group('base.group_erp_manager') or u.has_group('base.group_system'):
            return True
        cp = u.partner_id.commercial_partner_id or u.partner_id
        return bool(cp and cp.sudo().cafm_can_add_workers)

    @route(API + '/client/inv/policy', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def inv_policy(self, **kw):
        """What the crew may draw, per store — the settings screen's data."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        stores = self._stores(env)
        Item = env['care.cafm.stock.item'].sudo()
        sid = request.httprequest.args.get('store_id')
        dom = [('store_id', 'in', stores.ids)]
        if sid and sid.isdigit():
            dom.append(('store_id', '=', int(sid)))
        items = Item.search(dom, order='product_id')
        services = env['care.cafm.service'].sudo().search([])
        return _ok({
            'can_manage': self._may_set_policy(env),
            'services': [{'id': s.id, 'name': s.name, 'type': s.service_type} for s in services],
            'stores': [{'id': s.id, 'name': s.name, 'is_sub': s.is_sub,
                        'service': s.service_id.name or None,
                        'parent': s.parent_store_id.name or None,
                        'worker_issue_allowed': s.worker_issue_allowed} for s in stores],
            'items': [{
                'id': it.id, 'product': it.product_id.display_name,
                'store': it.store_id.name, 'store_id': it.store_id.id,
                'on_hand': it.on_hand, 'uom': it.uom_name or None,
                'allow_worker_issue': it.allow_worker_issue,
                'allowed_services': it.allowed_service_ids.mapped('name'),
                'allowed_service_ids': it.allowed_service_ids.ids,
                'max_issue_qty': it.max_issue_qty,
            } for it in items],
        })

    @route(API + '/client/inv/policy/item/<int:iid>', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def inv_policy_set(self, iid, **kw):
        """Client/admin sets whether the crew may draw this item, for which
        services, and the per-issue cap."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._may_set_policy(env):
            return _err('غير مسموح — الإعداد للعميل أو المدير فقط', 403)
        it = env['care.cafm.stock.item'].sudo().browse(iid).exists()
        if not it or it.store_id.id not in self._stores(env).ids:
            return _err('الصنف غير موجود', 404)
        b = _body()
        vals = {}
        if 'allow_worker_issue' in b:
            vals['allow_worker_issue'] = bool(b['allow_worker_issue'])
        if 'max_issue_qty' in b:
            vals['max_issue_qty'] = float(b['max_issue_qty'] or 0)
        if 'allowed_service_ids' in b:
            vals['allowed_service_ids'] = [(6, 0, [int(x) for x in (b['allowed_service_ids'] or [])])]
        if vals:
            it.write(vals)
        return _ok({
            'id': it.id, 'product': it.product_id.display_name,
            'allow_worker_issue': it.allow_worker_issue,
            'allowed_services': it.allowed_service_ids.mapped('name'),
            'allowed_service_ids': it.allowed_service_ids.ids,
            'max_issue_qty': it.max_issue_qty,
        })

    @route(API + '/client/inv/policy/store/<int:sid>', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def inv_policy_store(self, sid, **kw):
        """Toggle whether a whole store allows direct worker issue."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._may_set_policy(env):
            return _err('غير مسموح', 403)
        s = env['care.cafm.store'].sudo().browse(sid).exists()
        if not s or s.id not in self._stores(env).ids:
            return _err('المخزن غير موجود', 404)
        b = _body()
        if 'worker_issue_allowed' in b:
            s.worker_issue_allowed = bool(b['worker_issue_allowed'])
        return _ok({'id': s.id, 'name': s.name, 'worker_issue_allowed': s.worker_issue_allowed})

    # ---- movements --------------------------------------------------------
    @route(API + '/client/inv/moves', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def inv_moves(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        recs = self._move_search(env, kw)
        M = env['care.cafm.stock.move'].sudo()
        mt = _sel(M, 'move_type')
        return _ok([{
            'id': m.id, 'name': m.name, 'type': mt.get(m.move_type, m.move_type or ''),
            'type_raw': m.move_type, 'product': m.product_id.display_name,
            'store': m.store_id.name or None, 'quantity': m.quantity, 'uom': m.uom_name or None,
            'facility': m.facility_id.name or None, 'location': m.location_id.name or None,
            'building': m.building_id.name or None,
            'employee': _person_name(m.employee_id), 'date': _d(m.date),
            'total_cost': m.total_cost, 'state': m.state, 'note': m.note or None,
        } for m in recs])

    def _move_search(self, env, kw, limit=400):
        """Shared move query with drill-down filters used by /inv/moves and the
        consumption Excel export: type, facility, building, location, product,
        employee, period range, and a free-text search."""
        from odoo import fields as F
        M = env['care.cafm.stock.move'].sudo()
        dom = [('store_id', 'in', self._stores(env).ids)]
        if kw.get('type'):
            dom.append(('move_type', '=', kw['type']))
        for key, field in (('facility_id', 'facility_id'), ('building_id', 'building_id'),
                           ('location_id', 'location_id'), ('product_id', 'product_id'),
                           ('employee_id', 'employee_id')):
            v = kw.get(key)
            if v and str(v).isdigit():
                dom.append((field, '=', int(v)))
        period = kw.get('period')
        if period and period != 'all':
            tdy = F.Date.context_today(M)
            since = tdy if period == 'day' else (tdy.replace(month=1, day=1) if period == 'year' else tdy.replace(day=1))
            dom.append(('date', '>=', str(since)))
        q = (kw.get('q') or '').strip()
        if q:
            dom += ['|', '|', ('product_id.name', 'ilike', q), ('name', 'ilike', q), ('location_id.name', 'ilike', q)]
        return M.search(dom, order='date desc, id desc', limit=limit)

    @route('/cafm/inv/consumption/export', type='http', auth='public', methods=['GET'], csrf=False)
    def inv_consumption_export(self, **kw):
        """Consumption movements as Excel (via /web/sso like the other exports)."""
        from .client_api import _xlsx_response, _report_env
        env = _report_env()
        if not env:
            return request.redirect('/web/login')
        a = dict(request.httprequest.args)
        a.setdefault('type', 'issue')
        recs = self._move_search(env, a, limit=5000)
        mt = _sel(env['care.cafm.stock.move'].sudo(), 'move_type')
        columns = [_('#'), _('التاريخ'), _('المرجع'), _('المادة'), _('الكمية'), _('الوحدة'),
                   _('المرفق'), _('المبنى'), _('الموقع'), _('المنفّذ'), _('التكلفة'), _('النوع')]
        rows = []
        for i, m in enumerate(recs, 1):
            rows.append([i, _d(m.date) or '', m.name, m.product_id.display_name, m.quantity,
                         m.uom_name or '', m.facility_id.name or '', m.building_id.name or '',
                         m.location_id.name or '', (_person_name(m.employee_id) or ''),
                         round(m.total_cost, 2), mt.get(m.move_type, m.move_type or '')])
        meta = [
            (_('العميل'), env.user.partner_id.commercial_partner_id.name),
            (_('عدد الحركات'), len(recs)),
            (_('إجمالي الكمية'), round(sum(recs.mapped('quantity')), 1)),
            (_('إجمالي القيمة'), round(sum(recs.mapped('total_cost')), 2)),
        ]
        return _xlsx_response(_('تحليلات الاستهلاك'), columns, rows, 'consumption.xlsx', meta)

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
