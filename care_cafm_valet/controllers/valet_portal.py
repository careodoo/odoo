# -*- coding: utf-8 -*-
"""Valet parking on the web portal — the same kerbside console the app carries,
so an attendant on a desk terminal works the queue exactly like one on a phone:
take a car in, park it to a bay, answer a retrieval, hand it back with the fee.
"""
from markupsafe import Markup

from odoo import fields, http, _
from odoo.http import request

from odoo.addons.care_cafm.controllers.main import _shell, esc

ACCENT = '#b45309'

_STATE_COLOR = {
    'received': '#0891b2', 'parked': '#16a34a', 'requested': '#f59e0b',
    'delivered': '#64748b', 'cancelled': '#94a3b8',
}


class ValetPortal(http.Controller):

    def _facilities(self):
        """Sites this person covers: their client's, or the ones they work at —
        the same scoping the mobile API applies, so both surfaces agree."""
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
            if 'care.cafm.team' in env:
                ids |= set(env['care.cafm.team'].sudo().search(
                    [('member_ids', 'in', [emp.id])]).mapped('facility_id').ids)
        return Fac.browse(list(ids))

    # ---------------- board ----------------
    @http.route('/cafm/m/valet', type='http', auth='user', website=False)
    def board(self, state='live', **kw):
        env = request.env
        facs = self._facilities()
        T = env['care.valet.ticket'].sudo()
        dom = [('facility_id', 'in', facs.ids)]
        if state == 'live':
            dom.append(('state', 'in', ('received', 'parked', 'requested')))
        elif state != 'all':
            dom.append(('state', '=', state))
        tickets = T.search(dom, order='requested_at desc, received_at desc', limit=120)

        live = T.search([('facility_id', 'in', facs.ids),
                         ('state', 'in', ('received', 'parked', 'requested'))])
        today = fields.Date.context_today(env.user)
        out_today = T.search_count([('facility_id', 'in', facs.ids), ('state', '=', 'delivered'),
                                    ('delivered_at', '>=', '%s 00:00:00' % today)])
        counts = {s: len(live.filtered(lambda x, s=s: x.state == s))
                  for s in ('received', 'parked', 'requested')}

        emp = env.user.employee_id
        shift = env['care.valet.shift'].sudo().search(
            [('employee_id', '=', emp.id), ('state', '=', 'open')], limit=1) if emp else None

        body = self._kpis(counts, out_today, len(live.filtered('is_late')))
        body += self._shift_bar(shift, facs)
        body += self._zones(env['care.valet.zone'].sudo().search([('facility_id', 'in', facs.ids)]))
        body += self._filters(state, counts)
        body += self._intake_form(facs, env['care.valet.zone'].sudo().search(
            [('facility_id', 'in', facs.ids)]))
        if not tickets:
            body += Markup('<div class="card"><div class="muted">No vehicles in this status.</div></div>')
        for t in tickets:
            body += self._ticket_card(t, facs)
        return _shell('Valet Parking', body, accent=ACCENT)

    def _kpis(self, counts, out_today, late):
        return Markup(
            '<div class="kpi">'
            '<div><div class="n">%s</div><div class="l">Checked In</div></div>'
            '<div><div class="n">%s</div><div class="l">Parked</div></div>'
            '<div><div class="n">%s</div><div class="l">Requested</div></div>'
            '<div><div class="n">%s</div><div class="l">Delivered Today</div></div>'
            '<div><div class="n" style="color:%s">%s</div><div class="l">Overdue</div></div>'
            '</div>'
        ) % (counts.get('received', 0), counts.get('parked', 0), counts.get('requested', 0),
             out_today, '#f2603f' if late else '#14202b', late)

    def _shift_bar(self, shift, facs):
        if shift:
            return Markup(
                '<div class="card row" style="margin-top:11px">'
                '<div><div class="h4">🎫 %s</div>'
                '<div class="muted">%s tickets · fees %s · tips %s · cash due %s</div></div>'
                '<form method="post" action="/cafm/m/valet/shift/close">%s'
                '<button class="btn g" style="width:auto;margin:0;padding:9px 14px">Close Shift</button>'
                '</form></div>'
            ) % (esc(shift.name), shift.ticket_count, shift.total_fees, shift.total_tips,
                 shift.cash_due, self._csrf())
        if not facs:
            return Markup('')
        return Markup(
            '<form method="post" action="/cafm/m/valet/shift/open" class="card row" style="margin-top:11px">%s'
            '<div><div class="h4">No open shift</div>'
            '<div class="muted">Open a shift so tickets and cash are assigned to you.</div></div>'
            '<button class="btn" style="width:auto;margin:0;padding:9px 14px">Open Shift</button>'
            '</form>'
        ) % self._csrf()

    def _csrf(self):
        return Markup('<input type="hidden" name="csrf_token" value="%s"/>') % request.csrf_token()

    def _zones(self, zones):
        if not zones:
            return Markup('')
        out = Markup('<h3 style="margin:16px 0 9px">Zones and Occupancy</h3>')
        for z in zones:
            col = '#f2603f' if z.occupancy > 85 else '#37c98a'
            out += Markup(
                '<div class="card"><div class="row"><div class="h4">🅿️ %s</div>'
                '<span class="pill" style="background:rgba(55,201,138,.15);color:%s">%s available</span></div>'
                '<div style="background:#f4f6fa;border-radius:6px;height:8px;margin-top:8px;overflow:hidden">'
                '<div style="height:8px;width:%s%%;background:%s"></div></div>'
                '<div class="muted" style="margin-top:5px">%s occupied of %s · %s%%</div></div>'
            ) % (esc(z.name), col, z.free, min(100, int(z.occupancy or 0)), col,
                 z.occupied, z.capacity, round(z.occupancy or 0))
        return out

    def _filters(self, cur, counts):
        opts = [('live', 'All Active', ''), ('requested', 'Requested', counts.get('requested', 0)),
                ('parked', 'Parked', counts.get('parked', 0)),
                ('received', 'Awaiting Parking', counts.get('received', 0)),
                ('delivered', 'Delivered', ''), ('all', 'All', '')]
        out = Markup('<div style="display:flex;gap:7px;flex-wrap:wrap;margin:16px 0 11px">')
        for key, label, n in opts:
            sel = ('background:%s;color:#ffffff' % ACCENT) if key == cur else 'background:#ffffff;color:#71809a'
            txt = '%s (%s)' % (label, n) if n != '' else label
            out += Markup(
                '<a href="/cafm/m/valet?state=%s" class="pill" style="%s;padding:7px 12px">%s</a>'
            ) % (key, Markup(sel), esc(txt))
        return out + Markup('</div>')

    def _intake_form(self, facs, zones):
        """Taking a car in is the most frequent action, so it sits at the top of
        the queue rather than behind a separate page."""
        if not facs:
            return Markup('')
        fopts = Markup('').join(
            Markup('<option value="%s">%s</option>') % (f.id, esc(f.name)) for f in facs)
        zopts = Markup('<option value="">— None —</option>') + Markup('').join(
            Markup('<option value="%s">%s</option>') % (z.id, esc(z.name)) for z in zones)
        return Markup(
            '<details class="card"><summary style="font-weight:900;cursor:pointer">🚗 Check In New Vehicle</summary>'
            '<form method="post" action="/cafm/m/valet/create" style="margin-top:10px">%s'
            '<label>Plate Number *</label><input name="plate" required placeholder="12345 / ABC"/>'
            '<div class="grid" style="gap:8px">'
            '<div><label>Make</label><input name="car_make"/></div>'
            '<div><label>Model</label><input name="car_model"/></div>'
            '<div><label>Color</label><input name="car_color"/></div>'
            '<div><label>Key Number</label><input name="key_tag"/></div>'
            '<div><label>Guest Name</label><input name="guest_name"/></div>'
            '<div><label>Phone</label><input name="guest_phone"/></div></div>'
            '<label>Fees</label><input name="fee" type="number" step="0.001" value="0"/>'
            '<label>Facility</label><select name="facility_id">%s</select>'
            '<label>Zone</label><select name="zone_id">%s</select>'
            '<label>Vehicle condition notes (scratches…)</label><textarea name="damage_note" rows="2"></textarea>'
            '<button class="btn">Issue Ticket</button></form></details>'
        ) % (self._csrf(), fopts, zopts)

    def _ticket_card(self, t, facs):
        col = _STATE_COLOR.get(t.state, '#64748b')
        tags = Markup('')
        if t.spot_id:
            tags += Markup('<span class="pill ok">🅿️ %s</span> ') % esc(t.spot_id.name)
        if t.key_tag:
            tags += Markup('<span class="pill info">🔑 %s</span> ') % esc(t.key_tag)
        if t.has_damage:
            tags += Markup('<span class="pill crit">⚠ Damage Notes</span> ')
        if t.state == 'requested':
            cls = 'crit' if t.is_late else 'warn'
            tags += Markup('<span class="pill %s">⏱ %s min</span> ') % (cls, round(t.retrieval_minutes, 1))
        if t.fee:
            tags += Markup('<span class="pill info">%s KWD%s</span> ') % (
                t.fee, ' · Paid' if t.paid else '')

        act = Markup('')
        if t.state == 'received':
            free = request.env['care.valet.spot'].sudo().search(
                [('facility_id', '=', t.facility_id.id), ('state', '=', 'free')], limit=200)
            if free:
                opts = Markup('').join(
                    Markup('<option value="%s">%s — %s</option>') % (s.id, esc(s.name), esc(s.zone_id.name))
                    for s in free)
                act = Markup(
                    '<form method="post" action="/cafm/m/valet/%s/park">%s'
                    '<label>Select Spot</label><select name="spot_id" required>%s</select>'
                    '<button class="btn" style="background:#37c98a;color:#04201c">Park Vehicle</button></form>'
                ) % (t.id, self._csrf(), opts)
            else:
                act = Markup('<div class="muted" style="margin-top:8px">No spots available in this facility.</div>')
        elif t.state == 'parked':
            act = Markup(
                '<form method="post" action="/cafm/m/valet/%s/request">%s'
                '<button class="btn" style="background:#f59e0b;color:#221503">🔔 Request Retrieval</button></form>'
            ) % (t.id, self._csrf())
        if t.state in ('parked', 'requested'):
            act += Markup(
                '<details style="margin-top:8px"><summary class="muted" style="cursor:pointer">Hand Over to Guest</summary>'
                '<form method="post" action="/cafm/m/valet/%s/deliver">%s'
                '<div class="grid" style="gap:8px">'
                '<div><label>Fees</label><input name="fee" type="number" step="0.001" value="%s"/></div>'
                '<div><label>Tip</label><input name="tip" type="number" step="0.001" value="0"/></div></div>'
                '<label style="display:flex;gap:7px;align-items:center;margin-top:8px">'
                '<input type="checkbox" name="paid" value="1" checked style="width:auto;margin:0"/> Paid</label>'
                '<button class="btn">✔ Hand Over</button></form></details>'
            ) % (t.id, self._csrf(), t.fee or 0)

        act += Markup(
            '<a class="btn g" href="/valet/ticket/%s/print" target="_blank">🖨️ Print Ticket</a>'
        ) % t.id
        return Markup(
            '<div class="card stripe" style="border-inline-start-color:%s">'
            '<div class="row"><div class="h4">%s</div>'
            '<span class="pill" style="background:%s22;color:%s">%s</span></div>'
            '<div class="muted">%s</div>'
            '<div style="margin-top:7px">%s</div>%s</div>'
        ) % (col, esc(t.plate), Markup(col), Markup(col),
             esc(dict(t._fields['state'].selection).get(t.state, t.state)),
             esc(' · '.join(filter(None, [
                 ' '.join(filter(None, [t.car_make, t.car_model, t.car_color])),
                 t.guest_name or '', t.name or '']))),
             tags, act)

    # ---------------- actions ----------------
    @http.route('/cafm/m/valet/create', type='http', auth='user', methods=['POST'],
                website=False, csrf=True)
    def create(self, **post):
        env = request.env
        facs = self._facilities()
        plate = (post.get('plate') or '').strip()
        fid = int(post.get('facility_id') or 0) or (facs[:1].id if facs else 0)
        if not plate or fid not in facs.ids:
            return request.redirect('/cafm/m/valet')
        emp = env.user.employee_id
        shift = env['care.valet.shift'].sudo().search(
            [('employee_id', '=', emp.id), ('state', '=', 'open')], limit=1) if emp else None
        env['care.valet.ticket'].sudo().create({
            'plate': plate, 'facility_id': fid,
            'zone_id': int(post.get('zone_id') or 0) or False,
            'car_make': post.get('car_make') or False,
            'car_model': post.get('car_model') or False,
            'car_color': post.get('car_color') or False,
            'key_tag': post.get('key_tag') or False,
            'guest_name': post.get('guest_name') or False,
            'guest_phone': post.get('guest_phone') or False,
            'damage_note': post.get('damage_note') or False,
            'fee': float(post.get('fee') or 0),
            'received_by': emp.id if emp else False,
            'shift_id': shift.id if shift else False,
        })
        return request.redirect('/cafm/m/valet')

    @http.route('/cafm/m/valet/<int:tid>/<string:act>', type='http', auth='user',
                methods=['POST'], website=False, csrf=True)
    def action(self, tid, act, **post):
        env = request.env
        t = env['care.valet.ticket'].sudo().browse(tid).exists()
        if not t or t.facility_id.id not in self._facilities().ids:
            return request.redirect('/cafm/m/valet')
        emp = env.user.employee_id
        try:
            if act == 'park':
                if post.get('spot_id'):
                    t.spot_id = int(post['spot_id'])
                t.parked_by = emp.id if emp else False
                t.action_park()
            elif act == 'request':
                t.action_request()
            elif act == 'deliver':
                t.action_deliver(
                    by=(emp.id if emp else None),
                    fee=float(post['fee']) if post.get('fee') else None,
                    tip=float(post['tip']) if post.get('tip') else None,
                    paid=bool(post.get('paid')))
            elif act == 'cancel':
                t.action_cancel()
        except Exception:
            pass  # a rejected transition just re-renders the board
        return request.redirect('/cafm/m/valet')

    @http.route('/cafm/m/valet/shift/<string:act>', type='http', auth='user',
                methods=['POST'], website=False, csrf=True)
    def shift(self, act, **post):
        env = request.env
        emp = env.user.employee_id
        if not emp:
            return request.redirect('/cafm/m/valet')
        S = env['care.valet.shift'].sudo()
        cur = S.search([('employee_id', '=', emp.id), ('state', '=', 'open')], limit=1)
        if act == 'open' and not cur:
            facs = self._facilities()
            if facs:
                S.create({'employee_id': emp.id, 'facility_id': facs[0].id})
        elif act == 'close' and cur:
            cur.action_close()
        return request.redirect('/cafm/m/valet')
