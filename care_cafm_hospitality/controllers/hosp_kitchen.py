# -*- coding: utf-8 -*-
"""The kitchen display (KDS) and the client's consumption analytics.

The kitchen screen is built for a wall-mounted tablet in a noisy room: big
type, one colour per urgency, and a card that turns red before anyone has to
ask where the coffee is. It refreshes itself, because nobody in a kitchen is
going to pull-to-refresh with wet hands.
"""
from collections import defaultdict
from datetime import timedelta

from markupsafe import Markup

from odoo import fields, http, _
from odoo.http import request

from odoo.addons.care_cafm.controllers.main import _shell, esc
from .hosp_portal import HospPortal, _csrf, _bar, KITCHEN_ACCENT, STATS_ACCENT


class HospKitchen(HospPortal):

    # ================= live kitchen =================
    @http.route('/hosp/kitchen', type='http', auth='user', website=False)
    def kitchen(self, station=None, **kw):
        env = request.env
        facs = self._facilities()
        O = env['care.hosp.order'].sudo()
        dom = [('facility_id', 'in', facs.ids),
               ('state', 'in', ('placed', 'accepted', 'preparing', 'ready'))]
        orders = O.search(dom, order='placed_at asc')
        if station:
            sid = int(station)
            orders = orders.filtered(lambda o: sid in o.line_ids.mapped('station_id').ids)

        today = fields.Date.context_today(env.user)
        done_today = O.search_count([('facility_id', 'in', facs.ids), ('state', '=', 'delivered'),
                                     ('delivered_at', '>=', '%s 00:00:00' % today)])
        late = orders.filtered('is_late')
        pending_approval = O.search_count([('facility_id', 'in', facs.ids),
                                           ('state', '=', 'await_approval')])

        # the screen must not go stale on a wall-mounted tablet
        body = Markup('<script>setTimeout(function(){location.reload()},15000)</script>')
        body += Markup(
            '<div class="kpi">'
            '<div><div class="n">%s</div><div class="l">In Queue</div></div>'
            '<div><div class="n" style="color:%s">%s</div><div class="l">Late</div></div>'
            '<div><div class="n">%s</div><div class="l">Ready</div></div>'
            '<div><div class="n">%s</div><div class="l">Served Today</div></div>'
            '</div>'
        ) % (len(orders.filtered(lambda o: o.state != 'ready')),
             '#f2603f' if late else '#14202b', len(late),
             len(orders.filtered(lambda o: o.state == 'ready')), done_today)

        if pending_approval:
            body += Markup(
                '<a class="card" style="display:block;border-color:#a78bfa" href="/hosp/approvals">'
                '<div class="h4">🔐 %s order awaiting approval</div>'
                '<div class="muted">Click to review and approve.</div></a>') % pending_approval

        # station filter
        stations = env['care.hosp.station'].sudo().search([('facility_id', 'in', facs.ids)])
        if stations:
            body += Markup('<div style="display:flex;gap:7px;flex-wrap:wrap;margin:15px 0 11px">')
            sel = 'background:%s;color:#ffffff' % KITCHEN_ACCENT if not station else 'background:#ffffff;color:#71809a'
            body += Markup('<a href="/hosp/kitchen" class="pill" style="%s;padding:8px 13px">All Stations</a>') % Markup(sel)
            for s in stations:
                on = station and int(station) == s.id
                st = ('background:%s;color:#ffffff' % KITCHEN_ACCENT) if on else 'background:#ffffff;color:#71809a'
                n = len([o for o in orders if s.id in o.line_ids.mapped('station_id').ids])
                body += Markup('<a href="/hosp/kitchen?station=%s" class="pill" style="%s;padding:8px 13px">'
                               '%s %s (%s)</a>') % (s.id, Markup(st), s.icon or '🍳', esc(s.name), n)
            body += Markup('</div>')

        if not orders:
            body += Markup('<div class="card" style="text-align:center;padding:34px">'
                           '<div style="font-size:44px">✅</div>'
                           '<div class="h4" style="margin-top:8px">No orders in the queue</div>'
                           '<div class="muted">The screen refreshes automatically every 15 seconds.</div></div>')
        for o in orders:
            body += self._kds_card(o)
        return _shell('Kitchen Display', body, accent=KITCHEN_ACCENT, back='/cafm/m')

    def _kds_card(self, o):
        """One ticket. Colour is driven purely by how long it has waited against
        its own target — the crew reads urgency without reading numbers."""
        waited = o.wait_minutes or 0
        target = o.prep_target or 5
        ratio = waited / target if target else 0
        if o.state == 'ready':
            edge, badge = '#37c98a', Markup('<span class="pill ok">Ready — awaiting serving</span>')
        elif ratio >= 1:
            edge, badge = '#f2603f', Markup('<span class="pill crit">⚠ Late by %s min</span>') % int(waited)
        elif ratio >= 0.7:
            edge, badge = '#f5b638', Markup('<span class="pill warn">%s min</span>') % int(waited)
        else:
            edge, badge = '#4aa8ff', Markup('<span class="pill info">%s min</span>') % int(waited)

        lines = Markup('')
        for l in o.line_ids:
            lines += Markup(
                '<div style="padding:8px 0;border-top:1px solid #e6eaf0">'
                '<div style="font-size:16px;font-weight:900">%s × %s</div>'
                '%s%s</div>'
            ) % (esc(l.item_id.name), int(l.quantity),
                 Markup('<div style="color:%s;font-size:13px;font-weight:700;margin-top:2px">%s</div>')
                 % (Markup(KITCHEN_ACCENT), esc(l.option_label)) if l.option_label else Markup(''),
                 Markup('<div class="muted" style="margin-top:2px">📝 %s</div>') % esc(l.note)
                 if l.note else Markup(''))

        vip = Markup('<span class="pill crit">VIP</span> ') if o.is_vip else Markup('')
        typ = Markup('<span class="pill info">%s · %s guests</span> ') % (
            esc(dict(o._fields['order_type'].selection)[o.order_type]), o.guest_count) \
            if o.order_type != 'self' else Markup('')

        btns = Markup('<div style="display:flex;gap:8px;margin-top:10px">')
        if o.state == 'placed':
            btns += self._kbtn(o.id, 'accept', 'Accept', '#4aa8ff')
        if o.state in ('placed', 'accepted'):
            btns += self._kbtn(o.id, 'preparing', 'Start Preparation', '#f5b638')
        if o.state in ('placed', 'accepted', 'preparing'):
            btns += self._kbtn(o.id, 'ready', 'Ready', '#37c98a')
        if o.state in ('ready', 'preparing'):
            btns += self._kbtn(o.id, 'deliver', 'Served ✔', KITCHEN_ACCENT)
        btns += Markup('</div>')

        return Markup(
            '<div class="card stripe" style="border-inline-start-width:6px;border-inline-start-color:%s">'
            '<div class="row"><div><div style="font-size:18px;font-weight:900">%s</div>'
            '<div class="muted">%s · %s</div></div>%s</div>'
            '<div style="margin-top:6px">%s%s</div>%s%s</div>'
        ) % (Markup(edge), esc(o.name),
             esc(o.requester_id.name or ''), esc(o.room_label or o.location_id.name or '—'),
             badge, vip, typ, lines, btns)

    def _kbtn(self, oid, act, label, color):
        return Markup(
            '<form method="post" action="/hosp/kitchen/%s/%s" style="margin:0;flex:1">%s'
            '<button class="btn" style="background:%s;color:#ffffff;margin:0">%s</button></form>'
        ) % (oid, act, _csrf(), Markup(color), esc(label))

    @http.route('/hosp/kitchen/<int:oid>/<string:act>', type='http', auth='user',
                methods=['POST'], website=False, csrf=True)
    def kitchen_act(self, oid, act, **post):
        env = request.env
        o = env['care.hosp.order'].sudo().browse(oid).exists()
        if not o or o.facility_id.id not in self._facilities().ids:
            return request.redirect('/hosp/kitchen')
        try:
            {'accept': o.action_accept, 'preparing': o.action_preparing,
             'ready': o.action_ready, 'deliver': o.action_deliver,
             'reject': o.action_reject}.get(act, lambda: None)()
        except Exception:
            pass
        return request.redirect(request.httprequest.referrer or '/hosp/kitchen')

    # ================= approvals =================
    @http.route('/hosp/approvals', type='http', auth='user', website=False)
    def approvals(self, **kw):
        env = request.env
        orders = env['care.hosp.order'].sudo().search(
            [('facility_id', 'in', self._facilities().ids), ('state', '=', 'await_approval')])
        body = Markup('')
        if not orders:
            body = Markup('<div class="card"><div class="muted">No orders awaiting approval.</div></div>')
        for o in orders:
            items = ' · '.join('%s×%s' % (l.item_id.name, int(l.quantity)) for l in o.line_ids)
            body += Markup(
                '<div class="card stripe" style="border-inline-start-color:#a78bfa">'
                '<div class="h4">%s — %s</div>'
                '<div class="muted" style="margin-top:4px">%s</div>'
                '<div class="muted" style="margin-top:6px">🔐 %s</div>'
                '<div style="display:flex;gap:8px;margin-top:10px">'
                '<form method="post" action="/hosp/approve/%s" style="flex:1;margin:0">%s'
                '<button class="btn" style="margin:0">Approve</button></form>'
                '<form method="post" action="/hosp/kitchen/%s/reject" style="flex:1;margin:0">%s'
                '<button class="btn crit" style="margin:0">Reject</button></form></div></div>'
            ) % (esc(o.name), esc(o.requester_id.name or ''), esc(items),
                 esc(o.limit_note or ''), o.id, _csrf(), o.id, _csrf())
        return _shell('Order Approvals', body, accent='#a78bfa', back='/hosp/kitchen')

    @http.route('/hosp/approve/<int:oid>', type='http', auth='user',
                methods=['POST'], website=False, csrf=True)
    def approve(self, oid, **post):
        o = request.env['care.hosp.order'].sudo().browse(oid).exists()
        if o and o.facility_id.id in self._facilities().ids:
            o.action_approve()
        return request.redirect('/hosp/approvals')

    # ================= analytics =================
    @http.route('/hosp/stats', type='http', auth='user', website=False)
    def stats(self, days='30', **kw):
        env = request.env
        facs = self._facilities()
        try:
            ndays = max(1, min(365, int(days)))
        except ValueError:
            ndays = 30
        since = fields.Datetime.now() - timedelta(days=ndays)
        Line = env['care.hosp.order.line'].sudo()
        lines = Line.search([('facility_id', 'in', facs.ids),
                             ('order_id.placed_at', '>=', since),
                             ('order_state', 'not in', ('draft', 'cancelled', 'rejected'))])
        O = env['care.hosp.order'].sudo()
        orders = O.search([('facility_id', 'in', facs.ids), ('placed_at', '>=', since),
                           ('state', 'not in', ('draft', 'cancelled', 'rejected'))])

        total_items = sum(lines.mapped('quantity'))
        total_cost = sum(lines.mapped('line_cost'))
        delivered = orders.filtered(lambda o: o.state == 'delivered')
        avg_prep = (sum(delivered.mapped('prep_minutes')) / len(delivered)) if delivered else 0
        on_time = len(delivered.filtered(lambda o: o.prep_minutes <= (o.prep_target or 5)))
        sla = (100.0 * on_time / len(delivered)) if delivered else 0
        rated = delivered.filtered('rating')
        avg_rating = (sum(int(o.rating) for o in rated) / len(rated)) if rated else 0

        body = Markup('<div style="display:flex;gap:7px;flex-wrap:wrap;margin-bottom:13px">')
        for d, label in (('7', 'Last 7 days'), ('30', 'Last 30 days'), ('90', 'Last 90 days')):
            on = str(ndays) == d
            st = ('background:%s;color:#ffffff' % STATS_ACCENT) if on else 'background:#ffffff;color:#71809a'
            body += Markup('<a href="/hosp/stats?days=%s" class="pill" style="%s;padding:8px 13px">%s</a>') % (
                d, Markup(st), esc(label))
        body += Markup('</div>')

        body += Markup(
            '<div class="kpi">'
            '<div><div class="n">%s</div><div class="l">Total Items</div></div>'
            '<div><div class="n">%s</div><div class="l">Order Count</div></div>'
            '<div><div class="n">%s</div><div class="l">Cost (KWD)</div></div>'
            '</div>'
            '<div class="kpi" style="margin-top:9px">'
            '<div><div class="n">%s</div><div class="l">Avg Preparation (min)</div></div>'
            '<div><div class="n" style="color:%s">%s%%</div><div class="l">Target Compliance</div></div>'
            '<div><div class="n">%s</div><div class="l">Average Rating</div></div>'
            '</div>'
        ) % (int(total_items), len(orders), round(total_cost, 2),
             round(avg_prep, 1), '#37c98a' if sla >= 85 else '#f5b638', round(sla),
             ('%.1f ★' % avg_rating) if avg_rating else '—')

        body += self._rank(lines, 'requester_id', 'Top Consuming Users', '#8a6d3b', money=True)
        body += self._rank(lines, 'item_id', 'Most Ordered Items', '#0891b2')
        body += self._rank(lines, 'category_id', 'Consumption by Category', '#7c3aed', money=True)
        body += self._rank(lines, 'department_id', 'Consumption by Department', '#16a34a', money=True)
        body += self._hourly(orders)
        body += self._daily(orders)
        body += Markup(
            '<a class="btn g" href="/hosp/stats/export?days=%s">⬇️ Export CSV for analysis</a>') % ndays
        return _shell('Hospitality Statistics', body, accent=STATS_ACCENT, back='/hosp')

    def _rank(self, lines, field, title, color, money=False, limit=8):
        agg = defaultdict(lambda: [0.0, 0.0])
        for l in lines:
            rec = l[field]
            if not rec:
                continue
            agg[rec][0] += l.quantity
            agg[rec][1] += l.line_cost
        if not agg:
            return Markup('')
        rows = sorted(agg.items(), key=lambda kv: -kv[1][0])[:limit]
        top = rows[0][1][0] or 1
        out = Markup('<h3 style="margin:18px 0 9px">%s</h3><div class="card">') % esc(title)
        for rec, (qty, cost) in rows:
            label = '%s KWD' % round(cost, 2) if money else '%s' % int(qty)
            out += Markup(
                '<div style="padding:8px 0">'
                '<div class="row"><div class="h4">%s</div>'
                '<span class="muted">%s · %s</span></div>%s</div>'
            ) % (esc(rec.display_name), int(qty), esc(label), _bar(100.0 * qty / top, color, 7))
        return out + Markup('</div>')

    def _hourly(self, orders):
        """When the rush actually happens — this is what staffing decisions need."""
        buckets = defaultdict(int)
        for o in orders:
            if not o.placed_at:
                continue
            local = fields.Datetime.context_timestamp(o, o.placed_at)
            buckets[local.hour] += 1
        if not buckets:
            return Markup('')
        peak = max(buckets.values()) or 1
        out = Markup('<h3 style="margin:18px 0 9px">Peak Hours</h3>'
                     '<div class="card"><div style="display:flex;align-items:flex-end;'
                     'gap:3px;height:110px">')
        for h in range(6, 20):
            n = buckets.get(h, 0)
            ht = max(3, int(90.0 * n / peak))
            col = '#f2603f' if n == peak else STATS_ACCENT
            out += Markup(
                '<div style="flex:1;text-align:center">'
                '<div style="height:%spx;background:%s;border-radius:4px 4px 0 0" title="%s orders"></div>'
                '<div style="font-size:9px;color:#71809a;margin-top:3px">%s</div></div>'
            ) % (ht, Markup(col), n, h)
        return out + Markup('</div><div class="muted" style="margin-top:7px">'
                            'The bars show the number of orders per hour — red marks the peak time.</div></div>')

    def _daily(self, orders):
        buckets = defaultdict(int)
        for o in orders:
            if o.placed_at:
                buckets[fields.Datetime.context_timestamp(o, o.placed_at).date()] += 1
        if not buckets:
            return Markup('')
        days = sorted(buckets)[-21:]
        peak = max(buckets[d] for d in days) or 1
        out = Markup('<h3 style="margin:18px 0 9px">Daily Trend</h3>'
                     '<div class="card"><div style="display:flex;align-items:flex-end;gap:3px;height:90px">')
        for d in days:
            n = buckets[d]
            out += Markup('<div style="flex:1;background:#8a6d3b;border-radius:3px 3px 0 0;height:%spx" '
                          'title="%s: %s orders"></div>') % (max(3, int(76.0 * n / peak)), d, n)
        return out + Markup('</div><div class="muted" style="margin-top:7px">Last %s days.</div></div>') % len(days)

    @http.route('/hosp/stats/export', type='http', auth='user', website=False)
    def export(self, days='30', **kw):
        """CSV, because the client's finance team lives in a spreadsheet."""
        env = request.env
        try:
            ndays = max(1, min(365, int(days)))
        except ValueError:
            ndays = 30
        since = fields.Datetime.now() - timedelta(days=ndays)
        lines = env['care.hosp.order.line'].sudo().search(
            [('facility_id', 'in', self._facilities().ids),
             ('order_id.placed_at', '>=', since),
             ('order_state', 'not in', ('draft', 'cancelled', 'rejected'))])
        rows = ['﻿Order,Date,User,Department,Facility,Location,Category,Item,Specifications,Quantity,Cost,Status']
        for l in lines:
            o = l.order_id
            rows.append(','.join('"%s"' % str(v or '').replace('"', "'") for v in [
                o.name, str(o.placed_at or '')[:16], o.requester_id.name,
                o.department_id.name, o.facility_id.name, o.room_label or o.location_id.name,
                l.category_id.name, l.item_id.name, l.option_label,
                int(l.quantity), round(l.line_cost, 3),
                dict(o._fields['state'].selection).get(o.state, o.state)]))
        csv = '\n'.join(rows)
        return request.make_response(csv, headers=[
            ('Content-Type', 'text/csv; charset=utf-8'),
            ('Content-Disposition', 'attachment; filename="hospitality_%sd.csv"' % ndays)])

    # ================= client-side limit settings =================
    def _may_set_limits(self):
        """Consumption caps are the client's money and their staff's allowance —
        only an administrator or a user their client record trusts may touch
        them. This was writing global policy for any logged-in user."""
        env = request.env
        u = env.user
        if u.has_group('base.group_system') or u.has_group('base.group_erp_manager'):
            return True
        p = u.partner_id.commercial_partner_id or u.partner_id
        client = env['care.cafm.client'].sudo().search(
            [('partner_id', '=', p.id)], limit=1) if p else None
        return bool(client and client.can('inventory_policy'))

    @http.route('/hosp/limits', type='http', auth='user', website=False)
    def limits(self, **kw):
        env = request.env
        if not self._may_set_limits():
            return _shell('Consumption Limits', Markup(
                '<div class="card"><div class="h4">⛔ Not Authorized</div>'
                '<div class="muted">Setting consumption limits is available to client administrators only.</div></div>'),
                accent=STATS_ACCENT, back='/hosp')
        L = env['care.hosp.limit'].sudo()
        pols = L.search([])
        body = Markup(
            '<div class="card"><div class="muted">Define how much each user or department can order. '
            'When the limit is exceeded you can block the order, or route it for administrator approval — which is usually the '
            'better option so that a guest order is never rejected.</div></div>')
        for p in pols:
            caps = ' · '.join(filter(None, [
                '%s items' % p.max_items if p.max_items else '',
                '%s orders' % p.max_orders if p.max_orders else '',
                '%s KWD' % p.max_cost if p.max_cost else '']))
            scope = {'all': 'Everyone', 'user': 'Specific Users',
                     'department': 'Specific Departments'}.get(p.scope, p.scope)
            if p.scope == 'user' and p.user_ids:
                scope += ' (%s)' % ', '.join(p.user_ids.mapped('name')[:3])
            body += Markup(
                '<div class="card stripe" style="border-inline-start-color:%s">'
                '<div class="row"><div class="h4">%s</div>'
                '<span class="pill %s">%s</span></div>'
                '<div class="muted" style="margin-top:5px">%s · %s · %s</div>'
                '<form method="post" action="/hosp/limits/%s/save" style="margin-top:9px">%s'
                '<div class="grid" style="gap:8px">'
                '<div><label>Max Items</label><input name="max_items" type="number" value="%s"/></div>'
                '<div><label>Max Orders</label><input name="max_orders" type="number" value="%s"/></div>'
                '<div><label>Max Cost</label><input name="max_cost" type="number" step="0.001" value="%s"/></div>'
                '<div><label>Period</label><select name="period">%s</select></div></div>'
                '<label>On Exceed</label><select name="on_exceed">%s</select>'
                '<button class="btn">Save</button></form></div>'
            ) % (Markup(STATS_ACCENT), esc(p.name),
                 Markup('crit' if p.on_exceed == 'block' else 'warn'),
                 esc(dict(p._fields['on_exceed'].selection)[p.on_exceed]),
                 esc(scope), esc(dict(p._fields['period'].selection)[p.period]), esc(caps or 'No limit'),
                 p.id, _csrf(), p.max_items, p.max_orders, p.max_cost,
                 self._opts(p._fields['period'].selection, p.period),
                 self._opts(p._fields['on_exceed'].selection, p.on_exceed))
        body += Markup(
            '<details class="card"><summary style="font-weight:900;cursor:pointer">➕ New Policy</summary>'
            '<form method="post" action="/hosp/limits/new" style="margin-top:10px">%s'
            '<label>Policy Name *</label><input name="name" required/>'
            '<div class="grid" style="gap:8px">'
            '<div><label>Max Items</label><input name="max_items" type="number" value="0"/></div>'
            '<div><label>Max Orders</label><input name="max_orders" type="number" value="0"/></div>'
            '<div><label>Max Cost</label><input name="max_cost" type="number" step="0.001" value="0"/></div>'
            '<div><label>Period</label><select name="period">'
            '<option value="day">Daily</option><option value="week">Weekly</option>'
            '<option value="month">Monthly</option></select></div></div>'
            '<label>On Exceed</label><select name="on_exceed">'
            '<option value="approve">Needs Approval</option><option value="block">Block Order</option>'
            '<option value="warn">Warn Only</option></select>'
            '<button class="btn">Create</button></form></details>') % _csrf()
        return _shell('Consumption Limits', body, accent=STATS_ACCENT, back='/hosp/stats')

    def _opts(self, selection, current):
        out = Markup('')
        for val, label in selection:
            sel = ' selected' if val == current else ''
            out += Markup('<option value="%s"%s>%s</option>') % (val, Markup(sel), esc(label))
        return out

    @http.route('/hosp/limits/<int:lid>/save', type='http', auth='user',
                methods=['POST'], website=False, csrf=True)
    def limit_save(self, lid, **post):
        if not self._may_set_limits():
            return request.redirect('/hosp')
        p = request.env['care.hosp.limit'].sudo().browse(lid).exists()
        if p:
            p.write({'max_items': int(post.get('max_items') or 0),
                     'max_orders': int(post.get('max_orders') or 0),
                     'max_cost': float(post.get('max_cost') or 0),
                     'period': post.get('period') or p.period,
                     'on_exceed': post.get('on_exceed') or p.on_exceed})
        return request.redirect('/hosp/limits')

    @http.route('/hosp/limits/new', type='http', auth='user',
                methods=['POST'], website=False, csrf=True)
    def limit_new(self, **post):
        if not self._may_set_limits():
            return request.redirect('/hosp')
        name = (post.get('name') or '').strip()
        if name:
            request.env['care.hosp.limit'].sudo().create({
                'name': name, 'scope': 'all',
                'max_items': int(post.get('max_items') or 0),
                'max_orders': int(post.get('max_orders') or 0),
                'max_cost': float(post.get('max_cost') or 0),
                'period': post.get('period') or 'day',
                'on_exceed': post.get('on_exceed') or 'approve',
            })
        return request.redirect('/hosp/limits')
