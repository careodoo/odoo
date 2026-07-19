# -*- coding: utf-8 -*-
"""Hospitality portal — three audiences, three screens.

  /hosp          the requester: browse, customise, order, reorder the usual
  /hosp/kitchen  the station crew: a live queue that ages and shouts when late
  /hosp/stats    the client: who consumed what, when, and at what cost
  /hosp/limits   the client: caps per user, department or everyone

The requester's cart is simply a draft order — no session state to lose, and a
half-built order survives a closed browser.
"""
from collections import OrderedDict, defaultdict
from datetime import timedelta

from markupsafe import Markup

from odoo import fields, http, _
from odoo.http import request

from odoo.addons.care_cafm.controllers.main import _shell, esc

ACCENT = '#8a6d3b'
KITCHEN_ACCENT = '#e5484d'
STATS_ACCENT = '#0891b2'


def _csrf():
    return Markup('<input type="hidden" name="csrf_token" value="%s"/>') % request.csrf_token()


def _bar(pct, color='#8a6d3b', height=8):
    return Markup(
        '<div style="background:#f4f6fa;border-radius:6px;height:%spx;overflow:hidden">'
        '<div style="height:%spx;width:%s%%;background:%s"></div></div>'
    ) % (height, height, max(0, min(100, round(pct or 0))), Markup(color))


class HospPortal(http.Controller):

    # ================= helpers =================
    def _facilities(self):
        env = request.env
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
        return Fac.browse(list(ids)) or Fac.search([], limit=1)

    def _cart(self, create=False):
        """The open draft order for this user — our shopping cart."""
        env = request.env
        O = env['care.hosp.order'].sudo()
        cart = O.search([('requester_id', '=', env.user.id), ('state', '=', 'draft')],
                        limit=1, order='id desc')
        if not cart and create:
            facs = self._facilities()
            if not facs:
                return O
            emp = env.user.employee_id
            cart = O.create({
                'requester_id': env.user.id, 'facility_id': facs[0].id,
                'department_id': emp.department_id.id if emp and emp.department_id else False,
            })
        return cart

    # ================= requester =================
    @http.route('/hosp', type='http', auth='user', website=False)
    def menu(self, cat=None, **kw):
        env = request.env
        facs = self._facilities()
        Item = env['care.hosp.item'].sudo()
        cats = env['care.hosp.category'].sudo().search([])
        dom = [('available', '=', True)]
        if cat:
            dom.append(('category_id', '=', int(cat)))
        items = Item.search(dom)
        items = items.filtered(
            lambda i: (not i.facility_ids or (i.facility_ids & facs)))

        body = self._greeting()
        body += self._cart_bar()
        body += self._favourites()
        body += self._limits_strip()

        # category rail
        body += Markup('<div style="display:flex;gap:7px;flex-wrap:wrap;margin:16px 0 12px">')
        sel = 'background:%s;color:#ffffff' % ACCENT if not cat else 'background:#ffffff;color:#71809a'
        body += Markup('<a href="/hosp" class="pill" style="%s;padding:8px 13px">الكل</a>') % Markup(sel)
        for c in cats:
            on = cat and int(cat) == c.id
            style = ('background:%s;color:#ffffff' % c.color) if on else 'background:#ffffff;color:#71809a'
            body += Markup('<a href="/hosp?cat=%s" class="pill" style="%s;padding:8px 13px">%s %s</a>') % (
                c.id, Markup(style), c.icon or '', esc(c.name))
        body += Markup('</div>')

        # item grid, grouped by category so the menu reads like a menu
        by_cat = OrderedDict()
        for i in items.sorted(lambda x: (x.category_id.sequence, x.sequence)):
            by_cat.setdefault(i.category_id, env['care.hosp.item'])
            by_cat[i.category_id] |= i
        if not by_cat:
            body += Markup('<div class="card"><div class="muted">لا أصناف متاحة حاليًا.</div></div>')
        for c, its in by_cat.items():
            body += Markup('<h3 style="margin:16px 0 9px">%s %s</h3>') % (c.icon or '', esc(c.name))
            body += Markup('<div class="grid">')
            for i in its:
                servable = i.is_servable_now()
                dim = '' if servable else 'opacity:.45;'
                sub = i.unavailable_note or ''
                if servable:
                    sub = '%s د · %s د.ك' % (i.prep_minutes, i.unit_cost)
                elif not sub:
                    sub = 'خارج وقت التقديم (%02d:00–%02d:00)' % (i.serve_from, i.serve_to)
                href = ('/hosp/item/%s' % i.id) if servable else '#'
                body += Markup(
                    '<a class="tile" style="%s" href="%s"><div class="i">%s</div>'
                    '<div class="n">%s</div><div class="s">%s</div></a>'
                ) % (Markup(dim), href, i.icon or '☕', esc(i.name), esc(sub))
            body += Markup('</div>')
        return _shell('الضيافة', body, accent=ACCENT)

    def _greeting(self):
        env = request.env
        O = env['care.hosp.order'].sudo()
        mine_open = O.search_count([('requester_id', '=', env.user.id),
                                    ('state', 'in', ('placed', 'accepted', 'preparing', 'ready'))])
        today = fields.Date.context_today(env.user)
        mine_today = O.search_count([('requester_id', '=', env.user.id),
                                     ('placed_at', '>=', '%s 00:00:00' % today),
                                     ('state', 'not in', ('draft', 'cancelled', 'rejected'))])
        return Markup(
            '<div class="kpi">'
            '<div><div class="n">%s</div><div class="l">طلباتي الجارية</div></div>'
            '<div><div class="n">%s</div><div class="l">طلباتي اليوم</div></div>'
            '<div><a href="/hosp/orders" style="display:block"><div class="n">📜</div>'
            '<div class="l">سجل طلباتي</div></a></div></div>'
        ) % (mine_open, mine_today)

    def _cart_bar(self):
        cart = self._cart()
        if not cart or not cart.line_ids:
            return Markup('')
        lines = Markup('').join(Markup(
            '<div class="row" style="padding:6px 0;border-top:1px solid #e6eaf0">'
            '<div><div class="h4">%s × %s</div><div class="muted">%s%s</div></div>'
            '<form method="post" action="/hosp/line/%s/remove" style="margin:0">%s'
            '<button class="pill crit" style="border:none;cursor:pointer;font-family:inherit">حذف</button>'
            '</form></div>'
        ) % (esc(l.item_id.name), int(l.quantity), esc(l.option_label or '—'),
             esc(' · %s' % l.note) if l.note else '', l.id, _csrf()) for l in cart.line_ids)
        return Markup(
            '<div class="card" style="border-color:%s">'
            '<div class="row"><div class="h4">🛒 سلّتك (%s صنف)</div>'
            '<span class="pill info">%s د.ك</span></div>%s'
            '<form method="post" action="/hosp/place" style="margin-top:10px">%s'
            '<label>المكتب/القاعة</label><input name="room_label" value="%s" placeholder="مثال: مكتب المالية"/>'
            '<label>ملاحظات</label><input name="note" value="%s"/>'
            '<button class="btn">إرسال الطلب للمطبخ</button></form>'
            '<form method="post" action="/hosp/cart/clear" style="margin-top:6px">%s'
            '<button class="btn g">إفراغ السلّة</button></form></div>'
        ) % (Markup(ACCENT), cart.item_count, round(cart.total_cost, 3), lines, _csrf(),
             esc(cart.room_label or ''), esc(cart.note or ''), _csrf())

    def _favourites(self):
        env = request.env
        favs = env['care.hosp.favorite'].sudo().search(
            [('user_id', '=', env.user.id)], limit=6, order='times_used desc')
        if not favs:
            return Markup('')
        out = Markup('<h3 style="margin:16px 0 9px">⭐ طلبي المعتاد — بنقرة واحدة</h3>'
                     '<div style="display:flex;gap:8px;flex-wrap:wrap">')
        for f in favs:
            out += Markup(
                '<form method="post" action="/hosp/fav/%s/order" style="margin:0">%s'
                '<button class="card" style="border:1px solid %s;cursor:pointer;font-family:inherit;'
                'color:#14202b;text-align:start;margin:0;min-width:150px">'
                '<div class="h4">%s %s</div><div class="muted">%s</div></button></form>'
            ) % (f.id, _csrf(), Markup(ACCENT), f.item_id.icon or '☕', esc(f.item_id.name),
                 esc(' · '.join(f.option_ids.mapped('name')) or '—'))
        return out + Markup('</div>')

    def _limits_strip(self):
        """Show the cap before they hit it — nobody likes being refused at the
        end of a five-tap flow."""
        env = request.env
        usage = env['care.hosp.limit'].sudo().usage_for(env.user, self._facilities()[:1] or None)
        usage = [u for u in usage if u['max_items'] or u['max_cost']]
        if not usage:
            return Markup('')
        out = Markup('')
        for u in usage[:3]:
            if u['max_items']:
                pct = 100.0 * u['used_items'] / u['max_items']
                left = max(0, u['max_items'] - u['used_items'])
                label = '%s — المتبقّي لك %s من %s' % (u['policy'], left, u['max_items'])
            else:
                pct = 100.0 * u['used_cost'] / u['max_cost']
                label = '%s — استهلكت %s من %s د.ك' % (
                    u['policy'], round(u['used_cost'], 3), u['max_cost'])
            color = '#f2603f' if pct >= 100 else ('#f5b638' if pct >= 70 else '#37c98a')
            out += Markup('<div class="card"><div class="muted">%s</div>%s</div>') % (
                esc(label), _bar(pct, color, 7))
        return out

    @http.route('/hosp/item/<int:iid>', type='http', auth='user', website=False)
    def item(self, iid, **kw):
        env = request.env
        it = env['care.hosp.item'].sudo().browse(iid).exists()
        if not it:
            return request.redirect('/hosp')
        body = Markup(
            '<div class="card"><div style="font-size:44px;text-align:center">%s</div>'
            '<h2 style="text-align:center;margin:6px 0">%s</h2>'
            '<div class="muted" style="text-align:center">%s</div>'
            '<div class="row" style="margin-top:10px">'
            '<span class="pill info">⏱ %s دقيقة</span>'
            '<span class="pill info">%s د.ك</span></div></div>'
        ) % (it.icon or '☕', esc(it.name), esc(it.description or ''),
             it.prep_minutes, it.unit_cost)

        form = Markup('<form method="post" action="/hosp/add">%s'
                      '<input type="hidden" name="item_id" value="%s"/>') % (_csrf(), it.id)
        for g in it.option_group_ids.sorted('sequence'):
            req = ' <span class="pill crit">إلزامي</span>' if g.required else ''
            form += Markup('<div class="card"><div class="h4">%s%s</div>') % (esc(g.name), Markup(req))
            for o in g.option_ids.sorted('sequence'):
                extra = ' (+%s د.ك)' % o.extra_cost if o.extra_cost else ''
                kind = 'checkbox' if g.multi else 'radio'
                nm = 'opt_%s' % g.id
                checked = ' checked' if (o.is_default and not g.multi) else ''
                form += Markup(
                    '<label style="display:flex;align-items:center;gap:9px;padding:7px 0;'
                    'color:#14202b;font-weight:600;font-size:13.5px">'
                    '<input type="%s" name="%s" value="%s"%s style="width:auto;margin:0"/>%s%s</label>'
                ) % (kind, nm, o.id, Markup(checked), esc(o.name), esc(extra))
            form += Markup('</div>')
        form += Markup(
            '<div class="card">'
            '<label>الكمية</label><input type="number" name="quantity" value="1" min="1" max="20"/>'
            '<label>ملاحظة للمُحضِّر</label><input name="note" placeholder="مثال: كوب ورقي، بدون رغوة"/>'
            '<label style="display:flex;align-items:center;gap:9px;margin-top:10px;color:#14202b">'
            '<input type="checkbox" name="save_fav" value="1" style="width:auto;margin:0"/>'
            'احفظه في «طلبي المعتاد»</label>'
            '<button class="btn">أضف إلى السلّة</button></div></form>')
        return _shell(it.name, body + form, accent=ACCENT, back='/hosp')

    @http.route('/hosp/add', type='http', auth='user', methods=['POST'], website=False, csrf=True)
    def add(self, **post):
        env = request.env
        it = env['care.hosp.item'].sudo().browse(int(post.get('item_id') or 0)).exists()
        if not it:
            return request.redirect('/hosp')
        cart = self._cart(create=True)
        if not cart:
            return request.redirect('/hosp')
        opts = []
        for key, val in request.httprequest.form.lists():
            if key.startswith('opt_'):
                opts += [int(v) for v in val if v]
        qty = float(post.get('quantity') or 1)
        env['care.hosp.order.line'].sudo().create({
            'order_id': cart.id, 'item_id': it.id, 'quantity': max(1, qty),
            'option_ids': [(6, 0, opts)], 'note': post.get('note') or False,
        })
        if post.get('save_fav'):
            env['care.hosp.favorite'].sudo().create({
                'name': it.name, 'user_id': env.user.id, 'item_id': it.id,
                'option_ids': [(6, 0, opts)], 'quantity': max(1, qty),
                'note': post.get('note') or False,
            })
        return request.redirect('/hosp')

    @http.route('/hosp/line/<int:lid>/remove', type='http', auth='user',
                methods=['POST'], website=False, csrf=True)
    def remove_line(self, lid, **post):
        line = request.env['care.hosp.order.line'].sudo().browse(lid).exists()
        if line and line.order_id.requester_id.id == request.env.user.id \
                and line.order_id.state == 'draft':
            line.unlink()
        return request.redirect('/hosp')

    @http.route('/hosp/cart/clear', type='http', auth='user', methods=['POST'],
                website=False, csrf=True)
    def clear_cart(self, **post):
        cart = self._cart()
        if cart:
            cart.line_ids.unlink()
        return request.redirect('/hosp')

    @http.route('/hosp/place', type='http', auth='user', methods=['POST'],
                website=False, csrf=True)
    def place(self, **post):
        cart = self._cart()
        if not cart or not cart.line_ids:
            return request.redirect('/hosp')
        cart.write({'room_label': post.get('room_label') or cart.room_label,
                    'note': post.get('note') or cart.note})
        try:
            cart.action_place()
        except Exception as e:
            msg = str(getattr(e, 'args', [e])[0] if getattr(e, 'args', None) else e)
            return _shell('تعذّر الإرسال', Markup(
                '<div class="card"><div class="h4">⛔ لم يُرسَل الطلب</div>'
                '<div class="muted" style="margin-top:6px">%s</div>'
                '<a class="btn g" href="/hosp">رجوع للسلّة</a></div>') % esc(msg),
                accent=ACCENT, back='/hosp')
        return request.redirect('/hosp/orders')

    @http.route('/hosp/fav/<int:fid>/order', type='http', auth='user',
                methods=['POST'], website=False, csrf=True)
    def fav_order(self, fid, **post):
        env = request.env
        f = env['care.hosp.favorite'].sudo().browse(fid).exists()
        if not f or f.user_id.id != env.user.id:
            return request.redirect('/hosp')
        cart = self._cart(create=True)
        if not cart:
            return request.redirect('/hosp')
        env['care.hosp.order.line'].sudo().create({
            'order_id': cart.id, 'item_id': f.item_id.id, 'quantity': f.quantity or 1,
            'option_ids': [(6, 0, f.option_ids.ids)], 'note': f.note or False,
        })
        f.times_used += 1
        return request.redirect('/hosp')

    @http.route('/hosp/orders', type='http', auth='user', website=False)
    def my_orders(self, **kw):
        env = request.env
        orders = env['care.hosp.order'].sudo().search(
            [('requester_id', '=', env.user.id), ('state', '!=', 'draft')], limit=60)
        body = Markup('')
        live = orders.filtered(lambda o: o.state in ('placed', 'accepted', 'preparing', 'ready',
                                                     'await_approval'))
        if live:
            body += Markup('<h3 style="margin:4px 0 9px">الجاري الآن</h3>')
            body += Markup('<script>setTimeout(function(){location.reload()},20000)</script>')
        for o in live:
            body += self._my_order_card(o, live=True)
        past = orders - live
        if past:
            body += Markup('<h3 style="margin:18px 0 9px">السجل</h3>')
        for o in past[:40]:
            body += self._my_order_card(o, live=False)
        if not orders:
            body += Markup('<div class="card"><div class="muted">لا طلبات بعد.</div>'
                           '<a class="btn" href="/hosp">اطلب الآن</a></div>')
        return _shell('طلباتي', body, accent=ACCENT, back='/hosp')

    def _my_order_card(self, o, live):
        colors = {'await_approval': '#a78bfa', 'placed': '#4aa8ff', 'accepted': '#f5b638',
                  'preparing': '#f59e0b', 'ready': '#37c98a', 'delivered': '#64748b',
                  'rejected': '#f2603f', 'cancelled': '#94a3b8'}
        c = colors.get(o.state, '#64748b')
        items = ' · '.join('%s×%s%s' % (l.item_id.name, int(l.quantity),
                                        (' (%s)' % l.option_label) if l.option_label else '')
                           for l in o.line_ids)
        extra = Markup('')
        if o.state in ('placed', 'accepted', 'preparing'):
            eta = max(0, (o.prep_target or 5) - o.wait_minutes)
            cls = 'crit' if o.is_late else 'warn'
            txt = 'متأخر — %s دقيقة انتظار' % int(o.wait_minutes) if o.is_late \
                else 'متبقٍ ~%s دقيقة' % int(eta)
            extra = Markup('<span class="pill %s">⏱ %s</span>') % (Markup(cls), esc(txt))
        elif o.state == 'ready':
            extra = Markup('<span class="pill ok">🔔 جاهز للاستلام</span>')
        elif o.state == 'await_approval':
            extra = Markup('<span class="pill" style="background:rgba(167,139,250,.2);color:#a78bfa">'
                           'بانتظار موافقة المسؤول</span>')
        rate = Markup('')
        if o.state == 'delivered' and not o.rating:
            rate = Markup('<form method="post" action="/hosp/order/%s/rate" '
                          'style="margin-top:9px;display:flex;gap:6px">%s') % (o.id, _csrf())
            for n in ('5', '4', '3', '2', '1'):
                rate += Markup('<button name="rating" value="%s" class="pill info" '
                               'style="border:none;cursor:pointer;font-family:inherit;font-size:13px">'
                               '%s</button>') % (n, '★' * int(n))
            rate += Markup('</form>')
        elif o.rating:
            rate = Markup('<span class="pill ok">%s</span>') % ('★' * int(o.rating))
        return Markup(
            '<div class="card stripe" style="border-inline-start-color:%s">'
            '<div class="row"><div class="h4">%s</div>'
            '<span class="pill" style="background:%s22;color:%s">%s</span></div>'
            '<div class="muted" style="margin-top:4px">%s</div>'
            '<div class="muted" style="margin-top:4px;font-size:11px">%s · %s</div>'
            '<div style="margin-top:7px">%s %s</div></div>'
        ) % (Markup(c), esc(o.name), Markup(c), Markup(c),
             esc(dict(o._fields['state'].selection).get(o.state, o.state)),
             esc(items), esc(o.room_label or ''),
             esc(str(o.placed_at)[:16] if o.placed_at else ''), extra, rate)

    @http.route('/hosp/order/<int:oid>', type='http', auth='user', website=False)
    def order_detail(self, oid, **kw):
        """The deep-link target of a push notification."""
        env = request.env
        o = env['care.hosp.order'].sudo().browse(oid).exists()
        if not o:
            return request.redirect('/hosp/orders')
        if o.requester_id.id != env.user.id:
            return request.redirect('/hosp/kitchen')
        return _shell(o.name, self._my_order_card(o, live=True), accent=ACCENT, back='/hosp/orders')

    @http.route('/hosp/order/<int:oid>/rate', type='http', auth='user',
                methods=['POST'], website=False, csrf=True)
    def rate(self, oid, **post):
        o = request.env['care.hosp.order'].sudo().browse(oid).exists()
        if o and o.requester_id.id == request.env.user.id and post.get('rating'):
            o.rating = post['rating']
        return request.redirect('/hosp/orders')
