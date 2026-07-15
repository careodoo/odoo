# -*- coding: utf-8 -*-
"""CARE 2 CARE customer API — the home-services storefront: catalogue (home
feed, categories, services, packages), booking (create/list/cancel/rate) and
the customer account. Plus /whoami, a role-router so the unified app knows
which interfaces to show (c2c customer / cafm client / staff)."""
import base64

from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _abs, API

_TRANSPARENT_PNG = ('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk'
                    'YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')


def _sel(Model, field):
    try:
        return dict(Model.fields_get([field])[field].get('selection') or [])
    except Exception:
        return {}


def _d(v):
    return v and str(v) or None


def _img(model, rid, field='image'):
    return _abs('/web/image/%s/%s/%s' % (model, rid, field))


# public C2C image URLs (served with sudo so <img> tags render without a token)
# kind -> (model, field)
_C2C_IMG_MODELS = {
    'cat': ('c2c.category', 'image'),
    'svc': ('c2c.service', 'image'),
    'offer': ('c2c.offer', 'image'),
    'sub': ('c2c.subscription.plan', 'image'),
    'review': ('c2c.review', 'avatar'),
    'provider': ('c2c.provider', 'image'),
    'wbefore': ('c2c.work.sample', 'before_image'),
    'wafter': ('c2c.work.sample', 'after_image'),
}


def _c2c_img(kind, rid):
    return _abs('/api/v1/c2c/img/%s/%s' % (kind, rid))


class C2CClientApi(Controller):

    # ---- role router: which interfaces does this user get? ----------------
    @route(API + '/whoami', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def whoami(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        u = env.user
        p = u.partner_id
        is_staff = u.has_group('base.group_user')  # internal user
        is_admin = u.has_group('base.group_erp_manager') or u.has_group('base.group_system')
        # CAFM client: partner (or its company) owns a CAFM facility
        cafm = False
        if 'care.cafm.facility' in env:
            pids = {p.id}
            if p.commercial_partner_id:
                pids.add(p.commercial_partner_id.id)
                pids.update(env['res.partner'].sudo().search(
                    [('commercial_partner_id', '=', p.commercial_partner_id.id)]).ids)
            cafm = bool(env['care.cafm.facility'].sudo().search_count([('partner_id', 'in', list(pids))]))
        # PMS access: internal project users, or a member/manager/follower of any project
        pms = False
        if 'project.project' in env:
            if u.has_group('project.group_project_user') or u.has_group('project.group_project_manager'):
                pms = True
            else:
                Proj = env['project.project'].sudo()
                dom = ['|', '|', ('message_partner_ids', 'in', [p.id]), ('user_id', '=', u.id)]
                dom += [('member_ids', 'in', [u.id])] if 'member_ids' in Proj._fields else [('id', '=', 0)]
                pms = bool(Proj.search_count(dom))
        # CARE 2 CARE crew member (worker/leader/supervisor/driver/ops manager)
        prov = None
        if 'c2c.provider' in env:
            pr = env['c2c.provider'].sudo().search([('user_id', '=', u.id)], limit=1)
            if pr:
                prov = {'id': pr.id, 'name': pr.name, 'role': pr.role,
                        'role_label': dict(pr._fields['role'].selection).get(pr.role, pr.role),
                        'caps': pr.capabilities()}
        return _ok({
            'user': {'id': u.id, 'name': u.name, 'login': u.login, 'email': u.email or None,
                     'partner_id': p.id, 'avatar': _img('res.users', u.id, 'avatar_128') if u.image_128 else None},
            # everyone can use the C2C storefront; extra interfaces are additive
            'interfaces': {
                'c2c': True,
                'cafm': cafm,
                'pms': pms,
                'staff': is_staff,
                'admin': is_admin,
                'c2c_staff': bool(prov),
            },
            'provider': prov,
            'default': 'cafm' if cafm else 'c2c',
        })

    # ---- public image (sudo, no token needed) -----------------------------
    @route(API + '/c2c/img/<string:kind>/<int:rid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def c2c_img(self, kind, rid, **kw):
        spec = _C2C_IMG_MODELS.get(kind)
        data = None
        if spec:
            model, field = spec
            rec = request.env[model].sudo().browse(int(rid)).exists()
            if rec:
                data = rec[field]
        raw = base64.b64decode(data or _TRANSPARENT_PNG)
        return request.make_response(raw, headers=[
            ('Content-Type', 'image/png'), ('Content-Length', str(len(raw))),
            ('Cache-Control', 'public, max-age=86400'),
        ])

    # ---- home feed --------------------------------------------------------
    @route(API + '/c2c/home', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def c2c_home(self, **kw):
        env = _auth() or request.env  # public catalogue (guest browsing)
        if 'c2c.category' not in env:
            return _ok({'available': False})
        Cat = env['c2c.category'].sudo()
        Svc = env['c2c.service'].sudo()
        cats = Cat.search([], order='sequence, name')
        popular = Svc.search([('popular', '=', True)], limit=8)
        offers = env['c2c.offer'].sudo().search([('is_live', '=', True)], order='sequence', limit=8) if 'c2c.offer' in env else []
        featured = env['c2c.review'].sudo().search([('featured', '=', True)], limit=8) if 'c2c.review' in env else []
        subs = env['c2c.subscription.plan'].sudo().search([], order='sequence', limit=6) if 'c2c.subscription.plan' in env else []
        return _ok({
            'available': True,
            'categories': [self._cat(c) for c in cats],
            'popular': [self._svc(s) for s in popular],
            'offers': [self._offer(o) for o in offers],
            'reviews': [self._review(r) for r in featured],
            'subscriptions': [self._sub(p) for p in subs],
        })

    def _offer(self, o):
        return {'id': o.id, 'title': o.title, 'subtitle': o.subtitle or None, 'icon': o.icon or '🎉',
                'kind': o.kind, 'discount_pct': o.discount_pct, 'code': o.code or None,
                'color': o.color or '#0e3a5f', 'color2': o.color2 or '#17547f',
                'description': o.description or None, 'image': _c2c_img('offer', o.id)}

    def _review(self, r):
        return {'id': r.id, 'author': r.author_name, 'rating': int(r.rating or 0),
                'comment': r.comment or None, 'service': r.service_id.name or None,
                'date': _d(r.date), 'avatar': _c2c_img('review', r.id) if r.avatar else None}

    def _sub(self, p):
        return {'id': p.id, 'name': p.name, 'period': p.period, 'visits': p.visits,
                'price': p.price, 'old_price': p.old_price or None, 'save_pct': p.save_pct,
                'features': (p.features or '').split('\n') if p.features else [],
                'color': p.color or '#0e3a5f', 'popular': p.popular, 'category': p.category_id.name or None,
                'image': _c2c_img('sub', p.id)}

    def _cat(self, c):
        return {'id': c.id, 'name': c.name, 'icon': c.icon or '🧩', 'color': c.color or '#0e3a5f',
                'service_count': c.service_count,
                'image': _c2c_img('cat', c.id)}

    def _svc(self, s):
        pu = _sel(s, 'price_unit')
        return {'id': s.id, 'name': s.name, 'category': s.category_id.name or None,
                'category_id': s.category_id.id, 'category_icon': s.category_id.icon or '🧩',
                'price': s.base_price, 'currency': s.currency_id.name or '',
                'price_unit': pu.get(s.price_unit, s.price_unit or ''), 'price_unit_raw': s.price_unit,
                'duration_min': s.duration_min, 'rating': s.rating_avg, 'bookings': s.booking_count,
                'popular': s.popular, 'description': s.description or None,
                'image': _c2c_img('svc', s.id)}

    @route(API + '/c2c/categories', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def c2c_categories(self, **kw):
        env = _auth() or request.env  # public catalogue (guest browsing)
        if 'c2c.category' not in env:
            return _ok([])
        return _ok([self._cat(c) for c in env['c2c.category'].sudo().search([], order='sequence, name')])

    @route(API + '/c2c/services', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def c2c_services(self, **kw):
        env = _auth() or request.env  # public catalogue (guest browsing)
        if 'c2c.service' not in env:
            return _ok([])
        dom = []
        cid = request.httprequest.args.get('category_id')
        if cid and cid.isdigit():
            dom.append(('category_id', '=', int(cid)))
        q = (request.httprequest.args.get('q') or '').strip()
        if q:
            dom.append(('name', 'ilike', q))
        return _ok([self._svc(s) for s in env['c2c.service'].sudo().search(dom, order='popular desc, sequence')])

    @route(API + '/c2c/service/<int:sid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def c2c_service(self, sid, **kw):
        env = _auth() or request.env  # public catalogue (guest browsing)
        s = env['c2c.service'].sudo().browse(sid).exists()
        if not s:
            return _err('غير موجود', 404)
        d = self._svc(s)
        d['audience'] = s.audience
        d['packages'] = [{'id': p.id, 'name': p.name, 'description': p.description or None,
                          'price': p.price, 'duration_min': p.duration_min} for p in s.package_ids]
        # reviews  (note: a bare model recordset is falsy, so test `is not None`)
        Rev = env['c2c.review'].sudo() if 'c2c.review' in env else None
        d['reviews'] = [self._review(r) for r in Rev.search([('service_id', '=', s.id)], limit=20)] if Rev is not None else []
        d['rating_count'] = len(d['reviews'])
        # before/after gallery
        WS = env['c2c.work.sample'].sudo() if 'c2c.work.sample' in env else None
        d['work_samples'] = [{
            'id': w.id, 'title': w.title, 'note': w.note or None,
            'before': _c2c_img('wbefore', w.id) if w.before_image else None,
            'after': _c2c_img('wafter', w.id) if w.after_image else None,
        } for w in WS.search([('service_id', '=', s.id)], limit=12)] if WS is not None else []
        # team qualified for this category
        Prov = env['c2c.provider'].sudo() if 'c2c.provider' in env else None
        team = Prov.search([('category_ids', 'in', s.category_id.id)]) if Prov is not None else Prov
        if Prov is not None and not team:
            team = Prov.search([], limit=4)
        d['team'] = [{
            'id': p.id, 'name': p.name, 'rating': p.rating_avg, 'jobs': p.booking_count,
            'image': _c2c_img('provider', p.id) if p.image else None,
        } for p in (team or [])]
        return _ok(d)

    # ---- PRODUCT SHOP (buy materials) -------------------------------------
    def _product(self, p, pl=None):
        try:
            price = pl._get_product_price(p, 1.0) if pl else p.lst_price
        except Exception:
            price = p.lst_price
        return {
            'id': p.id, 'name': p.display_name, 'code': p.default_code or None,
            'price': round(price, 3), 'currency': self._cur().name,
            'uom': p.uom_id.name or None, 'category': p.categ_id.name or None,
            'category_id': p.categ_id.id,
            'image': _abs('/api/v1/product/%s/image' % p.id),
        }

    def _cur(self):
        return request.env.company.currency_id

    @route(API + '/c2c/products', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def c2c_products(self, **kw):
        env = _auth() or request.env
        Prod = env['product.product'].sudo()
        dom = [('sale_ok', '=', True), ('active', '=', True)]
        q = (request.httprequest.args.get('q') or '').strip()
        if q:
            dom += ['|', ('name', 'ilike', q), ('default_code', 'ilike', q)]
        cid = request.httprequest.args.get('category_id')
        if cid and cid.isdigit():
            dom.append(('categ_id', 'child_of', int(cid)))
        prods = Prod.search(dom, limit=300)
        cats = {}
        for p in prods:
            c = p.categ_id
            if c:
                cats[c.id] = {'id': c.id, 'name': c.name, 'count': cats.get(c.id, {}).get('count', 0) + 1}
        return _ok({
            'products': [self._product(p) for p in prods],
            'categories': sorted(cats.values(), key=lambda c: -c['count']),
        })

    @route(API + '/c2c/product/<int:pid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def c2c_product(self, pid, **kw):
        env = _auth() or request.env
        p = env['product.product'].sudo().browse(pid).exists()
        if not p:
            return _err('غير موجود', 404)
        d = self._product(p)
        d['description'] = (p.description_sale or '') or None
        return _ok(d)

    @route(API + '/c2c/order/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def c2c_order_create(self, **kw):
        env = _auth()
        if not env:
            return _err('سجّل الدخول لإتمام الشراء', 401)
        if 'c2c.product.order' not in env:
            return _err('غير متاح', 404)
        from .api import _body
        b = _body()
        lines = []
        for it in (b.get('items') or []):
            if it.get('product_id'):
                p = env['product.product'].sudo().browse(int(it['product_id'])).exists()
                if p:
                    lines.append((0, 0, {'product_id': p.id, 'quantity': float(it.get('quantity') or 1),
                                         'price_unit': float(it.get('price') or p.lst_price)}))
        if not lines:
            return _err('السلة فارغة', 422)
        rec = env['c2c.product.order'].sudo().create({
            'partner_id': env.user.partner_id.id, 'line_ids': lines,
            'address': b.get('address') or None, 'area': b.get('area') or None,
            'phone': b.get('phone') or env.user.partner_id.phone or None,
            'payment_method': b.get('payment_method') or 'cash',
        })
        rec.action_confirm()
        return _ok({'id': rec.id, 'name': rec.name, 'amount_total': rec.amount_total, 'state': rec.state})

    @route(API + '/c2c/orders', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def c2c_orders(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'c2c.product.order' not in env:
            return _ok([])
        st, ps = _sel(env['c2c.product.order'], 'state'), _sel(env['c2c.product.order'], 'payment_state')
        recs = env['c2c.product.order'].sudo().search([('partner_id', 'in', self._my_partner_ids(env))], order='id desc', limit=100)
        return _ok([{
            'id': o.id, 'name': o.name, 'amount_total': o.amount_total, 'item_count': o.item_count,
            'payment_label': ps.get(o.payment_state, o.payment_state or ''),
            'state': o.state, 'state_label': st.get(o.state, o.state or ''),
            'date': _d(o.create_date),
            'lines': [{'product': l.product_id.display_name, 'qty': l.quantity, 'subtotal': l.subtotal,
                       'image': _abs('/api/v1/product/%s/image' % l.product_id.id)} for l in o.line_ids],
        } for o in recs])

    # ---- available time slots (bookings + team schedule) ------------------
    @route(API + '/c2c/slots', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def c2c_slots(self, **kw):
        env = _auth() or request.env
        if 'c2c.settings' not in env:
            return _ok({'slots': [], 'available_days': []})
        sid = request.httprequest.args.get('service_id')
        date = request.httprequest.args.get('date')
        svc = env['c2c.service'].sudo().browse(int(sid)).exists() if sid and sid.isdigit() else None
        cfg = env['c2c.settings'].sudo().get_settings()
        slots = cfg.compute_slots(svc, date) if date else []
        # which weekdays are open (0=Mon..6=Sun) + horizon, so the app can gate the calendar
        open_days = [i for i in range(7) if cfg._working_day(i)]
        return _ok({
            'slots': slots,
            'open_weekdays': open_days,
            'lead_hours': cfg.lead_hours,
            'horizon_days': cfg.horizon_days,
            'slot_minutes': cfg.slot_minutes,
        })

    # ---- offers / subscriptions -------------------------------------------
    @route(API + '/c2c/offers', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def c2c_offers(self, **kw):
        env = _auth() or request.env
        if 'c2c.offer' not in env:
            return _ok([])
        return _ok([self._offer(o) for o in env['c2c.offer'].sudo().search([('is_live', '=', True)], order='sequence')])

    @route(API + '/c2c/subscriptions', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def c2c_subscriptions(self, **kw):
        env = _auth() or request.env
        if 'c2c.subscription.plan' not in env:
            return _ok([])
        return _ok([self._sub(p) for p in env['c2c.subscription.plan'].sudo().search([], order='sequence')])

    # ---- long-term / contract requests ------------------------------------
    @route(API + '/c2c/contract/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def c2c_contract_create(self, **kw):
        env = _auth() or request.env
        if 'c2c.contract.request' not in env:
            return _err('غير متاح', 404)
        from .api import _body
        b = _body()
        if not (b.get('title') and b.get('customer_name') and b.get('phone')):
            return _err('الاسم والهاتف وعنوان الطلب مطلوبة', 422)
        env2 = _auth()
        vals = {
            'title': b['title'], 'customer_name': b['customer_name'], 'phone': b['phone'],
            'email': b.get('email') or None, 'description': b.get('description') or None,
            'audience': b.get('audience') or 'company', 'site_address': b.get('site_address') or None,
            'duration_months': int(b.get('duration_months') or 12),
            'category_id': int(b['category_id']) if b.get('category_id') else False,
            'service_id': int(b['service_id']) if b.get('service_id') else False,
        }
        if env2:
            vals['partner_id'] = env2.user.partner_id.id
        rec = env['c2c.contract.request'].sudo().create(vals)
        return _ok({'id': rec.id, 'name': rec.name, 'state': rec.state})

    @route(API + '/c2c/contract/<int:cid>/<string:decision>', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def c2c_contract_decide(self, cid, decision, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        r = env['c2c.contract.request'].sudo().browse(cid).exists()
        if not r or r.partner_id.id not in self._my_partner_ids(env):
            return _err('غير موجود', 404)
        if decision == 'approve' and r.state == 'quoted':
            r.action_approve()
        elif decision == 'reject' and r.state in ('quoted', 'new', 'reviewing'):
            r.action_reject()
        else:
            return _err('لا يمكن تنفيذ الإجراء', 422)
        return _ok({'id': r.id, 'state': r.state})

    @route(API + '/c2c/contracts', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def c2c_contracts(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'c2c.contract.request' not in env:
            return _ok([])
        st = _sel(env['c2c.contract.request'], 'state')
        recs = env['c2c.contract.request'].sudo().search(
            [('partner_id', 'in', self._my_partner_ids(env))], order='id desc', limit=100)
        return _ok([{
            'id': r.id, 'name': r.name, 'title': r.title, 'category': r.category_id.name or None,
            'duration_months': r.duration_months, 'quote_amount': r.quote_amount or None,
            'quote_period': r.quote_period, 'quote_note': r.quote_note or None,
            'state': r.state, 'state_label': st.get(r.state, r.state or ''),
        } for r in recs])

    # ---- bookings ---------------------------------------------------------
    def _partner(self, env):
        return env.user.partner_id.commercial_partner_id or env.user.partner_id

    def _my_partner_ids(self, env):
        p = env.user.partner_id
        ids = {p.id}
        if p.commercial_partner_id:
            ids.add(p.commercial_partner_id.id)
            ids.update(env['res.partner'].sudo().search(
                [('commercial_partner_id', '=', p.commercial_partner_id.id)]).ids)
        return list(ids)

    def _booking(self, b):
        st, ps, pm = _sel(b, 'state'), _sel(b, 'payment_state'), _sel(b, 'payment_method')
        return {
            'id': b.id, 'name': b.name, 'service': b.service_id.name or None,
            'service_id': b.service_id.id, 'category_icon': b.category_id.icon or '🧩',
            'package': b.package_id.name if b.package_id else None,
            'visit': _d(b.visit_datetime), 'duration_min': b.duration_min,
            'address': b.address or None, 'area': b.area or None, 'phone': b.phone or None,
            'provider': b.provider_id.name if b.provider_id else None,
            'amount': b.amount, 'currency': b.currency_id.name or '',
            'payment_method': pm.get(b.payment_method, b.payment_method or ''), 'payment_method_raw': b.payment_method,
            'payment_state': b.payment_state, 'payment_label': ps.get(b.payment_state, b.payment_state or ''),
            'state': b.state, 'state_label': st.get(b.state, b.state or ''),
            'rating': b.rating, 'feedback': b.feedback or None, 'notes': b.notes or None,
        }

    @route(API + '/c2c/book', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def c2c_book(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'c2c.booking' not in env:
            return _err('غير متاح', 404)
        from .api import _body
        b = _body()
        if not b.get('service_id') or not b.get('visit'):
            return _err('الخدمة وموعد الزيارة مطلوبان', 422)
        vals = {
            'partner_id': env.user.partner_id.id,
            'service_id': int(b['service_id']),
            'visit_datetime': b['visit'],
            'address': b.get('address') or None, 'area': b.get('area') or None,
            'gps': b.get('gps') or None, 'phone': b.get('phone') or env.user.partner_id.phone or None,
            'payment_method': b.get('payment_method') or 'cash',
            'notes': b.get('notes') or None,
        }
        if b.get('package_id'):
            vals['package_id'] = int(b['package_id'])
        try:
            rec = env['c2c.booking'].sudo().create(vals)
            # apply a promo/offer code if valid
            code = (b.get('code') or '').strip()
            if code and 'c2c.offer' in env:
                off = env['c2c.offer'].sudo().search([('code', '=ilike', code), ('is_live', '=', True)], limit=1)
                if off and off.discount_pct and rec.amount:
                    disc = round(rec.amount * off.discount_pct / 100.0, 2)
                    rec.write({'discount_code': off.code, 'discount_amount': disc, 'amount': rec.amount - disc})
            rec.action_confirm()
        except Exception as e:
            return _err(str(e), 422)
        return _ok(self._booking(rec))

    @route(API + '/c2c/coupon', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def c2c_coupon(self, **kw):
        """Validate a coupon code and return its discount %, for a live preview."""
        env = _auth() or request.env
        code = (request.httprequest.args.get('code') or '').strip()
        if not code or 'c2c.offer' not in env:
            return _ok({'valid': False})
        off = env['c2c.offer'].sudo().search([('code', '=ilike', code), ('is_live', '=', True)], limit=1)
        if not off:
            return _ok({'valid': False})
        return _ok({'valid': True, 'code': off.code, 'discount_pct': off.discount_pct, 'title': off.title})

    @route(API + '/c2c/bookings', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def c2c_bookings(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'c2c.booking' not in env:
            return _ok([])
        dom = [('partner_id', 'in', self._my_partner_ids(env))]
        if kw.get('state'):
            dom.append(('state', '=', kw['state']))
        recs = env['c2c.booking'].sudo().search(dom, order='visit_datetime desc, id desc', limit=200)
        return _ok([self._booking(b) for b in recs])

    @route(API + '/c2c/booking/<int:bid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def c2c_booking(self, bid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        b = env['c2c.booking'].sudo().browse(bid).exists()
        if not b or b.partner_id.id not in self._my_partner_ids(env):
            return _err('غير موجود', 404)
        return _ok(self._booking(b))

    @route(API + '/c2c/booking/<int:bid>/cancel', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def c2c_cancel(self, bid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        b = env['c2c.booking'].sudo().browse(bid).exists()
        if not b or b.partner_id.id not in self._my_partner_ids(env):
            return _err('غير موجود', 404)
        if b.state in ('done', 'cancelled'):
            return _err('لا يمكن الإلغاء', 422)
        b.action_cancel()
        return _ok(self._booking(b))

    @route(API + '/c2c/booking/<int:bid>/rate', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def c2c_rate(self, bid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        from .api import _body
        b = env['c2c.booking'].sudo().browse(bid).exists()
        if not b or b.partner_id.id not in self._my_partner_ids(env):
            return _err('غير موجود', 404)
        body = _body()
        stars = int(body.get('rating') or 0)
        if stars < 1 or stars > 5:
            return _err('التقييم من 1 إلى 5', 422)
        b.action_rate(stars, body.get('feedback'))
        return _ok(self._booking(b))

    # ---- customer account -------------------------------------------------
    @route(API + '/c2c/account', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def c2c_account(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        p = env.user.partner_id
        bookings = env['c2c.booking'].sudo().search([('partner_id', 'in', self._my_partner_ids(env))]) if 'c2c.booking' in env else None
        upcoming = active = spent = 0
        if bookings is not None:
            from odoo import fields as F
            now = F.Datetime.now()
            upcoming = len(bookings.filtered(lambda b: b.visit_datetime and b.visit_datetime >= now and b.state not in ('done', 'cancelled')))
            active = len(bookings.filtered(lambda b: b.state in ('confirmed', 'assigned', 'in_progress')))
            spent = sum(bookings.filtered(lambda b: b.payment_state == 'paid').mapped('amount'))
        return _ok({
            'name': p.name, 'phone': p.phone or None, 'email': p.email or None,
            'total_bookings': len(bookings) if bookings is not None else 0,
            'upcoming': upcoming, 'active': active, 'total_spent': round(spent, 2),
            'currency': env.company.currency_id.name or '',
        })
