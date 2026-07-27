# -*- coding: utf-8 -*-
"""API التصاريح (Gate passes / Permits):
- الإصدار: العميل / مدير المشروع / المشرف (ومن له مرافق في نطاقه).
- الحارس: يُدخل/يُخرج الأشخاص فقط (تسجيل دخول/خروج متكرر لمتعدد الدخول، مرّة للفردي).
- نوعان: متعدد الدخول وفردي. مبنيّ على security.gate.pass وسجلّ الزيارات."""
import logging
from odoo import fields, _
from odoo.http import Controller, route
from .api import _auth, _ok, _err, _body, API

_logger = logging.getLogger(__name__)


class PermitsApi(Controller):

    # ================= صلاحيات ونطاق =================
    def _is_manager(self, env):
        return bool(env.user.has_group('base.group_erp_manager')
                    or env.user.has_group('base.group_system')
                    or env.user.has_group('security_management.group_security_manager'))

    def _issuer_facilities(self, env):
        F = env['care.cafm.facility'].sudo()
        if self._is_manager(env):
            return F.search([])
        facs = F.browse()
        if 'care.cafm.project' in env:
            projs = env['care.cafm.project'].sudo().search(
                ['|', ('manager_ids', 'in', [env.uid]), ('manager_id', '=', env.uid)])
            facs |= projs.mapped('facility_ids')
        p = env.user.partner_id
        pids = {p.id}
        if p.commercial_partner_id:
            pids.add(p.commercial_partner_id.id)
            pids.update(env['res.partner'].sudo().search(
                [('commercial_partner_id', '=', p.commercial_partner_id.id)]).ids)
        if 'care.cafm.client' in env:
            for cp in env['care.cafm.client'].sudo().search([('user_ids', 'in', [env.uid])]).mapped('partner_id'):
                pids.add(cp.id)
                pids.update(env['res.partner'].sudo().search([('commercial_partner_id', '=', cp.id)]).ids)
        facs |= F.search([('partner_id', 'in', list(pids))])
        return facs

    def _premises_of(self, env, facs):
        if 'security.premise' not in env:
            return None
        return env['security.premise'].sudo().search([('cafm_facility_id', 'in', facs.ids)]) if facs else env['security.premise'].sudo().browse()

    def _guard_premises(self, env):
        if 'security.employee' not in env:
            return None
        me = env['security.employee'].sudo().search([('employee_id.user_id', '=', env.uid)], limit=1)
        teams = me.team_ids if (me and 'team_ids' in me._fields) else env['security.team'].sudo().browse()
        if 'security.guard' in env:
            g = env['security.guard'].sudo().search(
                ['|', ('user_id', '=', env.uid), ('security_employee_id', 'in', me.ids if me else [])], limit=1)
            if g and 'security_employee_team_ids' in g._fields:
                teams |= g.security_employee_team_ids
        return teams.mapped('premise_id') if teams else env['security.premise'].sudo().browse()

    def _premise_guard_users(self, env, premise):
        """مستخدمو حرّاس فِرَق هذا الموقع (لإشعارهم بتصريح جديد)."""
        users = env['res.users']
        if not premise or 'security.team' not in env:
            return users
        teams = env['security.team'].sudo().search([('premise_id', '=', premise.id)])
        se = teams.mapped('member_ids') | teams.mapped('leader_id')
        if 'security.guard' in env:
            guards = env['security.guard'].sudo().search([('security_employee_team_ids', 'in', teams.ids)])
            se |= guards.mapped('security_employee_id')
        for m in se:
            if m.employee_id and m.employee_id.user_id:
                users |= m.employee_id.user_id
        return users

    def _notify(self, env, users, title, body, url=None, ntype='info'):
        try:
            if users and 'care.cafm.notification' in env:
                env['care.cafm.notification'].sudo().push(users, title, body, ntype=ntype, action_url=url)
        except Exception:
            pass

    # ================= تسلسل =================
    def _dict(self, env, gp, full=False):
        F = gp._fields
        d = {
            'id': gp.id, 'name': gp.name or None,
            'visitor': gp.visitor_name or (gp.visitor_id.name if gp.visitor_id else None),
            'phone': gp.visitor_phone or None, 'company': gp.visitor_company or None,
            'premise': gp.premise_id.name if gp.premise_id else None,
            'premise_id': gp.premise_id.id if gp.premise_id else None,
            'client': gp.client_id.name if gp.client_id else None,
            'purpose': gp.purpose or None,
            'valid_from': str(gp.valid_from or '')[:16] or None,
            'valid_until': str(gp.valid_until or '')[:16] or None,
            'state': gp.state, 'state_label': dict(F['state'].selection).get(gp.state, gp.state),
            'is_multi_entry': bool(gp.is_multi_entry),
            'current_inside': gp.current_inside, 'entries_count': gp.entries_count,
            'pass_type': gp.pass_type, 'qr_text': gp.qr_code_text or None,
        }
        if full:
            logs = env['security.visit.log'].sudo().search(
                [('gate_pass_id', '=', gp.id)], order='event_time desc', limit=100)
            d['logs'] = [{
                'id': l.id, 'type': l.event_type,
                'type_label': _('دخول') if l.event_type == 'check_in' else (_('خروج') if l.event_type == 'check_out' else l.event_type),
                'at': str(l.event_time or '')[:19], 'by': l.recorded_by.name if l.recorded_by else None,
                'note': l.note or None,
            } for l in logs]
        return d

    def _stats(self, env, GP, dom):
        return {
            'total': GP.search_count(dom),
            'active': GP.search_count(dom + [('state', 'in', ('approved', 'valid'))]),
            'inside': sum(GP.search(dom + [('state', 'in', ('approved', 'valid'))]).mapped('current_inside')),
            'expired': GP.search_count(dom + [('state', '=', 'expired')]),
        }

    # ================= خيارات الإصدار =================
    @route(API + '/permits/options', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def options(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        prem = self._premises_of(env, self._issuer_facilities(env))
        return _ok({
            'can_issue': self._is_manager(env) or bool(prem),
            'premises': [{'id': p.id, 'name': p.name,
                          'facility': p.cafm_facility_id.name if p.cafm_facility_id else None,
                          'client_id': p.client_id.id if p.client_id else None} for p in (prem or [])],
            'pass_types': [{'value': 'personal', 'label': _('شخصي')}, {'value': 'vehicle', 'label': _('مركبة')}],
        })

    # ================= إنشاء تصريح (مُصدِر) =================
    @route(API + '/permits/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'security.gate.pass' not in env:
            return _err('خدمة التصاريح غير مفعّلة', 404)
        prem = self._premises_of(env, self._issuer_facilities(env))
        if not self._is_manager(env) and not prem:
            return _err('لا تملك صلاحية إصدار تصاريح', 403)
        b = _body() or {}
        try:
            pid = int(b['premise_id'])
        except (KeyError, TypeError, ValueError):
            return _err('الموقع مطلوب', 422)
        if not self._is_manager(env) and pid not in (prem.ids if prem else []):
            return _err('موقع خارج نطاقك', 403)
        premise = env['security.premise'].sudo().browse(pid).exists()
        if not premise:
            return _err('موقع غير موجود', 404)
        name = (b.get('visitor') or '').strip()
        if not name:
            return _err('اسم الزائر مطلوب', 422)
        Partner = env['res.partner'].sudo()
        visitor = Partner.search([('name', '=', name)], limit=1)
        if not visitor:
            visitor = Partner.create({'name': name, 'phone': b.get('phone') or False})
        vf = b.get('valid_from') or fields.Datetime.to_string(fields.Datetime.now())
        vu = b.get('valid_until') or fields.Datetime.to_string(fields.Datetime.now() + __import__('datetime').timedelta(days=1))
        vals = {
            'visitor_id': visitor.id, 'client_id': premise.client_id.id if premise.client_id else False,
            'premise_id': premise.id, 'purpose': (b.get('purpose') or '-'),
            'valid_from': vf, 'valid_until': vu,
            'pass_type': b.get('pass_type') if b.get('pass_type') in ('personal', 'vehicle') else 'personal',
            'is_multi_entry': bool(b.get('is_multi_entry')),
        }
        if b.get('license_plate') and 'license_plate' in env['security.gate.pass']._fields:
            vals['license_plate'] = b['license_plate']
        try:
            gp = env['security.gate.pass'].sudo().create(vals)
            # اعتماد فوري لأن المُصدِر صاحب صلاحية
            gp.write({'state': 'approved', 'approved_by': env.uid, 'approved_date': fields.Datetime.now()})
            if hasattr(gp, 'action_generate_qr_code'):
                try:
                    gp.action_generate_qr_code()
                except Exception:
                    pass
        except Exception as e:
            return _err('تعذّر إنشاء التصريح: %s' % e, 400)
        # إشعار حرّاس الموقع بتصريح جديد يحتاج إدخال/إخراج أشخاص
        self._notify(env, self._premise_guard_users(env, premise), '🚪 تصريح جديد',
                     '%s — %s%s' % (gp.visitor_name or name, premise.name,
                                    ' (متعدد الدخول)' if gp.is_multi_entry else ''),
                     url='/permits/%s' % gp.id)
        return _ok(self._dict(env, gp, full=True))

    # ================= قوائمي (حسب الدور) =================
    @route(API + '/permits/mine', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def mine(self, scope=None, state=None, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'security.gate.pass' not in env:
            return _ok({'items': [], 'stats': {}, 'can_issue': False, 'is_guard': False})
        GP = env['security.gate.pass'].sudo()
        is_mgr = self._is_manager(env)
        issuer_prem = self._premises_of(env, self._issuer_facilities(env))
        guard_prem = self._guard_premises(env)
        is_guard = bool(guard_prem)
        can_issue = is_mgr or bool(issuer_prem)
        # النطاق: المدير كل شيء؛ المُصدِر ما أصدره أو على مواقعه؛ الحارس مواقع فريقه
        if is_mgr:
            dom = []
        elif scope == 'guard' and is_guard:
            dom = [('premise_id', 'in', guard_prem.ids)]
        elif can_issue:
            dom = ['|', ('create_uid', '=', env.uid), ('premise_id', 'in', issuer_prem.ids if issuer_prem else [])]
        elif is_guard:
            dom = [('premise_id', 'in', guard_prem.ids)]
        else:
            return _ok({'items': [], 'stats': {}, 'can_issue': False, 'is_guard': False})
        fdom = list(dom)
        if state and state != 'all':
            fdom = fdom + [('state', '=', state)]
        recs = GP.search(fdom, order='create_date desc', limit=150)
        return _ok({
            'items': [self._dict(env, g) for g in recs],
            'stats': self._stats(env, GP, dom),
            'can_issue': can_issue, 'is_guard': is_guard,
        })

    @route(API + '/permits/<int:pid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def detail(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        gp = env['security.gate.pass'].sudo().browse(pid).exists()
        if not gp:
            return _err('غير موجود', 404)
        return _ok(self._dict(env, gp, full=True))

    # ================= الحارس: إدخال/إخراج الأشخاص =================
    @route(API + '/permits/<int:pid>/entry', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def entry(self, pid, **kw):
        return self._visit(pid, 'in')

    @route(API + '/permits/<int:pid>/exit', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def exit(self, pid, **kw):
        return self._visit(pid, 'out')

    def _visit(self, pid, direction):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        gp = env['security.gate.pass'].sudo().browse(pid).exists()
        if not gp:
            return _err('التصريح غير موجود', 404)
        b = _body() or {}
        try:
            gp.api_record_visit(direction, person=b.get('person'), id_number=b.get('id_number'),
                                lat=b.get('lat'), lng=b.get('lng'), note=b.get('note'))
        except Exception as e:
            return _err(str(e), 400)
        # إشعار مُصدِر التصريح بحركة الدخول/الخروج
        if gp.create_uid and gp.create_uid.id != env.uid:
            lbl = 'دخل' if direction == 'in' else 'خرج'
            self._notify(env, gp.create_uid, '🚪 حركة تصريح',
                         '%s %s %s' % (b.get('person') or 'زائر', lbl, gp.premise_id.name or ''),
                         url='/permits/%s' % gp.id)
        return _ok(self._dict(env, gp, full=True))
