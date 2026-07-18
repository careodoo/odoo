# -*- coding: utf-8 -*-
"""CARE 2 CARE crew (staff) API — role-scoped operations for the five field
roles: worker / team-leader / supervisor / driver / ops-manager.

Every endpoint resolves the logged-in user to their c2c.provider record and
gates both data (which bookings are visible) and actions (start/complete/
assign/quality/approve) by ``provider.capabilities()``. A user with no
provider record gets 403 — the staff surface is invisible to customers."""
import base64

from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _body, _abs, API


def _d(v):
    return v and str(v) or None


_STATE_FLOW = ['draft', 'confirmed', 'assigned', 'in_progress', 'done', 'cancelled']


class C2CStaffApi(Controller):

    # ------------------------------------------------------------------ utils
    def _me(self, env):
        """The c2c.provider for the current user, or None."""
        if 'c2c.provider' not in env:
            return None
        return env['c2c.provider'].sudo().search([('user_id', '=', env.user.id)], limit=1) or None

    def _can(self, me, cap):
        return cap in (me.capabilities().get('can') or [])

    def _book_dict(self, b, full=False):
        d = {
            'id': b.id, 'name': b.name,
            'service': b.service_id.name if b.service_id else None,
            'category': b.category_id.name if b.category_id else None,
            'category_icon': b.category_id.icon if (b.category_id and 'icon' in b.category_id._fields) else None,
            'customer': b.partner_id.name if b.partner_id else None,
            'phone': b.phone or (b.partner_id.mobile or b.partner_id.phone if b.partner_id else None),
            'address': b.address or None, 'area': b.area or None, 'gps': b.gps or None,
            'visit': _d(b.visit_datetime), 'end': _d(b.end_datetime),
            'amount': b.amount, 'currency': b.currency_id.name if b.currency_id else '',
            'provider': b.provider_id.name if b.provider_id else None,
            'provider_id': b.provider_id.id if b.provider_id else None,
            'state': b.state, 'state_label': dict(b._fields['state'].selection).get(b.state, b.state),
            'quality_ok': b.quality_ok,
        }
        if full:
            d.update({
                'notes': b.notes or None, 'staff_note': b.staff_note or None,
                'started_at': _d(b.started_at), 'finished_at': _d(b.finished_at),
                'payment_state': b.payment_state, 'payment_method': b.payment_method,
                'before': _abs('/web/image/c2c.booking/%s/proof_before' % b.id) if b.proof_before else None,
                'after': _abs('/web/image/c2c.booking/%s/proof_after' % b.id) if b.proof_after else None,
                'rating': b.rating, 'feedback': b.feedback or None,
            })
        return d

    # --------------------------------------------------------------- identity
    @route(API + '/c2c/staff/whoami', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def staff_whoami(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        me = self._me(env)
        if not me:
            return _err('لست عضوًا في فريق CARE 2 CARE', 403)
        caps = me.capabilities()
        team = me.team_ids()
        return _ok({
            'id': me.id, 'name': me.name, 'role': me.role,
            'role_label': dict(me._fields['role'].selection).get(me.role, me.role),
            'phone': me.phone or None,
            'image': _abs('/api/v1/c2c/img/provider/%s' % me.id) if me.image else None,
            'available': me.available,
            'caps': caps,
            'leader': me.leader_id.name if me.leader_id else None,
            'supervisor': me.supervisor_id.name if me.supervisor_id else None,
            'team': [{'id': p.id, 'name': p.name, 'role': p.role,
                      'role_label': dict(p._fields['role'].selection).get(p.role, p.role),
                      'available': p.available} for p in team if p.id != me.id],
        })

    # ----------------------------------------------------------- availability
    @route(API + '/c2c/staff/available', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def staff_available(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        me = self._me(env)
        if not me:
            return _err('غير مصرّح', 403)
        me.available = bool(_body().get('available'))
        return _ok({'available': me.available})

    # ------------------------------------------------------------------- jobs
    @route(API + '/c2c/staff/jobs', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def staff_jobs(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        me = self._me(env)
        if not me:
            return _err('غير مصرّح', 403)
        Book = env['c2c.booking'].sudo()
        dom = me.booking_domain()
        f = kw.get('filter')
        if f == 'today':
            from odoo import fields as _f
            today = _f.Date.context_today(Book)
            dom = dom + [('visit_datetime', '>=', '%s 00:00:00' % today),
                         ('visit_datetime', '<=', '%s 23:59:59' % today)]
        elif f == 'open':
            dom = dom + [('state', 'in', ('assigned', 'in_progress'))]
        elif f == 'unassigned':
            dom = dom + [('provider_id', '=', False), ('state', 'in', ('confirmed', 'assigned'))]
        elif f == 'done':
            dom = dom + [('state', '=', 'done')]
        elif kw.get('state'):
            dom = dom + [('state', '=', kw['state'])]
        recs = Book.search(dom, order='visit_datetime asc', limit=200)
        return _ok([self._book_dict(b) for b in recs])

    @route(API + '/c2c/staff/job/<int:bid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def staff_job(self, bid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        me = self._me(env)
        if not me:
            return _err('غير مصرّح', 403)
        b = env['c2c.booking'].sudo().browse(bid).exists()
        if not b or (me.capabilities()['scope'] != 'all' and b.id not in env['c2c.booking'].sudo().search(me.booking_domain()).ids):
            return _err('غير موجود', 404)
        return _ok(self._book_dict(b, full=True))

    # ------------------------------------------------------------ KPI overview
    @route(API + '/c2c/staff/overview', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def staff_overview(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        me = self._me(env)
        if not me:
            return _err('غير مصرّح', 403)
        Book = env['c2c.booking'].sudo()
        base = me.booking_domain()
        from odoo import fields as _f
        today = _f.Date.context_today(Book)
        day = [('visit_datetime', '>=', '%s 00:00:00' % today), ('visit_datetime', '<=', '%s 23:59:59' % today)]
        team = me.team_ids()
        return _ok({
            'today': Book.search_count(base + day),
            'open': Book.search_count(base + [('state', 'in', ('assigned', 'in_progress'))]),
            'unassigned': Book.search_count(base + [('provider_id', '=', False), ('state', 'in', ('confirmed', 'assigned'))]),
            'done_today': Book.search_count(base + day + [('state', '=', 'done')]),
            'in_progress': Book.search_count(base + [('state', '=', 'in_progress')]),
            'team_size': len(team) - 1,
            'team_available': len(team.filtered('available')) - (1 if me.available else 0),
        })

    # -------------------------------------------------------------- actions
    @route(API + '/c2c/staff/job/<int:bid>/<string:act>', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def staff_job_action(self, bid, act, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        me = self._me(env)
        if not me:
            return _err('غير مصرّح', 403)
        b = env['c2c.booking'].sudo().browse(bid).exists()
        if not b:
            return _err('غير موجود', 404)
        # visibility gate (ops manager sees all)
        if me.capabilities()['scope'] != 'all' and b.id not in env['c2c.booking'].sudo().search(me.booking_domain()).ids:
            return _err('غير مصرّح لهذا الطلب', 403)
        body = _body()
        cap_map = {'start': 'start', 'complete': 'complete', 'proof': 'proof',
                   'assign': 'assign', 'quality': 'quality', 'approve': 'approve',
                   'reassign': 'reassign', 'note': 'view'}
        need = cap_map.get(act)
        if need and not self._can(me, need):
            return _err('لا تملك صلاحية هذا الإجراء', 403)
        try:
            if act == 'start':
                b.action_start()
            elif act == 'complete':
                if body.get('note'):
                    b.staff_note = body['note']
                b.action_done()
            elif act == 'proof':
                kind = body.get('kind', 'after')
                img = body.get('image')
                if not img:
                    return _err('الصورة مطلوبة', 422)
                if ',' in img:
                    img = img.split(',', 1)[1]
                b.write({'proof_before' if kind == 'before' else 'proof_after': img})
            elif act == 'note':
                b.staff_note = body.get('note') or b.staff_note
            elif act in ('assign', 'reassign'):
                # either a single member, or a whole crew (every member is notified)
                tid = body.get('team_leader_id')
                if tid:
                    leader = env['c2c.provider'].sudo().browse(int(tid)).exists()
                    if not leader:
                        return _err('الفريق غير موجود', 404)
                    b.action_assign_team(leader)
                    b.message_post(body='👥 أسند %s الطلب إلى فريق %s' % (me.name, leader.name))
                else:
                    pid = body.get('provider_id')
                    if not pid:
                        return _err('اختر عضو الفريق أو الفريق', 422)
                    target = env['c2c.provider'].sudo().browse(int(pid)).exists()
                    if not target:
                        return _err('العضو غير موجود', 404)
                    b.provider_id = target.id
                    if b.state in ('draft', 'confirmed'):
                        b.state = 'assigned'
                    b.message_post(body='👷 تم إسناد الطلب إلى %s بواسطة %s' % (target.name, me.name))
                    if target.user_id and 'care.cafm.notification' in env:
                        try:
                            env['care.cafm.notification'].sudo().push(
                                target.user_id, '🆕 طلب جديد مُسند إليك',
                                '%s — %s' % (b.service_id.name or '', b.area or b.address or ''),
                                ntype='task')
                        except Exception:
                            pass
            elif act == 'quality':
                b.write({'quality_ok': True, 'quality_by': me.id})
                b.message_post(body='✅ اعتماد الجودة بواسطة %s' % me.name)
            elif act == 'approve':
                if b.state == 'done' and b.payment_state != 'paid':
                    b.action_pay()
                b.message_post(body='🏁 اعتماد إغلاق الطلب بواسطة %s' % me.name)
            else:
                return _err('إجراء غير معروف', 400)
        except Exception as e:
            return _err(str(e), 422)
        return _ok(self._book_dict(b, full=True))

    # ------------------------------------------------- crews (for assignment)
    @route(API + '/c2c/staff/teams', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def staff_teams(self, **kw):
        """Every crew available for assignment: its leader, its own driver, each
        member's live status, and how loaded the crew currently is."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        me = self._me(env)
        if not me:
            return _err('غير مصرّح', 403)
        if not (self._can(me, 'assign') or self._can(me, 'manage_team')):
            return _err('غير مصرّح', 403)
        P = env['c2c.provider'].sudo()
        Book = env['c2c.booking'].sudo()
        # crews = providers that actually lead a crew
        leaders = P.search([('role', 'in', ('team_leader', 'supervisor')), ('active', '=', True)])
        leaders = leaders.filtered(lambda l: l.team_member_ids)
        roles = dict(P._fields['role'].selection)
        out = []
        for l in leaders:
            members = l.team_member_ids
            crew = l | members
            active_jobs = Book.search_count([
                '|', ('team_leader_id', '=', l.id), ('provider_id', 'in', crew.ids),
                ('state', 'in', ('assigned', 'in_progress'))])
            free = len(crew.filtered('available'))
            out.append({
                'id': l.id, 'name': l.name,
                'leader': {'id': l.id, 'name': l.name, 'available': l.available,
                           'phone': l.phone or None},
                'driver': ({'id': l.driver_id.id, 'name': l.driver_id.name,
                            'available': l.driver_id.available, 'phone': l.driver_id.phone or None}
                           if l.driver_id else None),
                'members': [{
                    'id': m.id, 'name': m.name, 'role': m.role,
                    'role_label': roles.get(m.role, m.role),
                    'available': m.available, 'phone': m.phone or None,
                    'rating': m.rating_avg,
                    'load': Book.search_count([('provider_id', '=', m.id),
                                               ('state', 'in', ('assigned', 'in_progress'))]),
                } for m in members],
                'size': len(crew), 'free': free, 'active_jobs': active_jobs,
                # a crew is "available" when it has someone free and isn't buried
                'status': 'busy' if active_jobs >= max(1, len(crew)) else ('free' if free else 'off'),
                'categories': l.category_ids.mapped('name'),
            })
        out.sort(key=lambda t: (t['status'] != 'free', t['active_jobs']))
        return _ok(out)

    # --------------------------------------------------------- team roster
    @route(API + '/c2c/staff/team', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def staff_team(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        me = self._me(env)
        if not me:
            return _err('غير مصرّح', 403)
        if not self._can(me, 'assign') and not self._can(me, 'manage_team'):
            return _err('غير مصرّح', 403)
        team = me.team_ids().filtered(lambda p: p.id != me.id)
        Book = env['c2c.booking'].sudo()
        out = []
        for p in team:
            load = Book.search_count([('provider_id', '=', p.id), ('state', 'in', ('assigned', 'in_progress'))])
            out.append({'id': p.id, 'name': p.name, 'role': p.role,
                        'role_label': dict(p._fields['role'].selection).get(p.role, p.role),
                        'available': p.available, 'phone': p.phone or None,
                        'image': _abs('/api/v1/c2c/img/provider/%s' % p.id) if p.image else None,
                        'rating': p.rating_avg, 'load': load})
        return _ok(out)
