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


# public C2C image URL (served with sudo so <img> tags render without a token)
_C2C_IMG_MODELS = {'cat': 'c2c.category', 'svc': 'c2c.service'}


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
        return _ok({
            'user': {'id': u.id, 'name': u.name, 'login': u.login, 'email': u.email or None,
                     'partner_id': p.id, 'avatar': _img('res.users', u.id, 'avatar_128') if u.image_128 else None},
            # everyone can use the C2C storefront; extra interfaces are additive
            'interfaces': {
                'c2c': True,
                'cafm': cafm,
                'staff': is_staff,
                'admin': is_admin,
            },
            'default': 'cafm' if cafm else 'c2c',
        })

    # ---- public image (sudo, no token needed) -----------------------------
    @route(API + '/c2c/img/<string:kind>/<int:rid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def c2c_img(self, kind, rid, **kw):
        model = _C2C_IMG_MODELS.get(kind)
        data = None
        if model:
            rec = request.env[model].sudo().browse(int(rid)).exists()
            if rec:
                data = rec.image
        raw = base64.b64decode(data or _TRANSPARENT_PNG)
        return request.make_response(raw, headers=[
            ('Content-Type', 'image/png'), ('Content-Length', str(len(raw))),
            ('Cache-Control', 'public, max-age=86400'),
        ])

    # ---- home feed --------------------------------------------------------
    @route(API + '/c2c/home', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def c2c_home(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'c2c.category' not in env:
            return _ok({'available': False})
        Cat = env['c2c.category'].sudo()
        Svc = env['c2c.service'].sudo()
        cats = Cat.search([], order='sequence, name')
        popular = Svc.search([('popular', '=', True)], limit=8)
        return _ok({
            'available': True,
            'categories': [self._cat(c) for c in cats],
            'popular': [self._svc(s) for s in popular],
        })

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
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'c2c.category' not in env:
            return _ok([])
        return _ok([self._cat(c) for c in env['c2c.category'].sudo().search([], order='sequence, name')])

    @route(API + '/c2c/services', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def c2c_services(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
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
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        s = env['c2c.service'].sudo().browse(sid).exists()
        if not s:
            return _err('غير موجود', 404)
        d = self._svc(s)
        d['audience'] = s.audience
        d['packages'] = [{'id': p.id, 'name': p.name, 'description': p.description or None,
                          'price': p.price, 'duration_min': p.duration_min} for p in s.package_ids]
        return _ok(d)

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
            rec.action_confirm()
        except Exception as e:
            return _err(str(e), 422)
        return _ok(self._booking(rec))

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
