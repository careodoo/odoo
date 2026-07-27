# -*- coding: utf-8 -*-
"""أدوات مشرف الأمن: إنشاء وإسناد المهام والدوريات والتصاريح وسجلات التفتيش.
كل النقاط تتحقّق أن المستخدم مشرف (قائد فريق أو دوره Supervisor أو مدير)، ثم
تنشئ السجل في وحدة security_management مع اشتقاق العميل/الموقع من فريق المشرف
عند عدم إرسالها. متاحة أيضاً للعميل (كامل الصلاحيات) عبر التحقّق من نطاقه."""
from odoo import fields, _
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _body, API


class SecuritySupervisorApi(Controller):

    # ---- تحديد المشرف ونطاقه -------------------------------------------
    def _my_guard(self, env):
        return env['security.guard'].sudo().search([('user_id', '=', env.uid)], limit=1)

    def _my_teams(self, env):
        """فرق المشرف: التي يقودها أو عضو فيها."""
        g = self._my_guard(env)
        se = g.security_employee_id if g else None
        if not se:
            return env['security.team'].sudo().browse()
        return env['security.team'].sudo().search(
            ['|', ('leader_id', '=', se.id), ('member_ids', 'in', [se.id])])

    def _client_teams(self, env):
        """فرق مواقع العميل (لتمكين العميل من الإنشاء على مواقعه)."""
        if 'care.cafm.facility' not in env or 'security.premise' not in env:
            return env['security.team'].sudo().browse()
        p = env.user.partner_id
        pids = {p.id, p.commercial_partner_id.id} if p.commercial_partner_id else {p.id}
        if 'care.cafm.client' in env:
            for c in env['care.cafm.client'].sudo().search([('user_ids', 'in', [env.uid])]):
                if c.partner_id:
                    pids.add(c.partner_id.id)
        facs = env['care.cafm.facility'].sudo().search([('partner_id', 'in', list(pids))])
        prem = env['security.premise'].sudo().search([('cafm_facility_id', 'in', facs.ids)]) if facs else None
        if not prem:
            return env['security.team'].sudo().browse()
        return env['security.team'].sudo().search([('premise_id', 'in', prem.ids)])

    def _scope_teams(self, env):
        """فرق المستخدم للإنشاء: مشرف (فرقه) أو عميل (فرق مواقعه) أو مدير (الكل)."""
        u = env.user
        if u.has_group('base.group_erp_manager') or u.has_group('base.group_system'):
            return env['security.team'].sudo().search([])
        teams = self._my_teams(env)
        if teams:
            return teams
        return self._client_teams(env)  # عميل

    def _can_manage(self, env):
        return bool(self._scope_teams(env))

    def _default_client(self, env):
        t = self._scope_teams(env)
        return t[:1].client_id if t else (env['security.client'].sudo().search([], limit=1))

    def _default_premise(self, env):
        t = self._scope_teams(env)
        prem = t.mapped('premise_id')
        return prem[:1] if prem else env['security.premise'].sudo().search([], limit=1)

    # ---- قوائم الخيارات للنماذج ----------------------------------------
    @route(API + '/security/sup/options', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def sup_options(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_manage(env):
            return _err('غير مصرّح — للمشرفين والعملاء فقط', 403)
        teams = self._scope_teams(env)
        # الحراس ضمن نطاق المستخدم (أعضاء الفرق)
        guards = teams.mapped('member_ids').mapped('guard_ids') if hasattr(teams.mapped('member_ids'), 'guard_ids') else env['security.guard'].sudo().search([('security_employee_id', 'in', teams.mapped('member_ids').ids)])
        prem = teams.mapped('premise_id')
        routes = env['security.patrol.route'].sudo().search([('premise_id', 'in', prem.ids)]) if ('security.patrol.route' in env and prem) else env['security.patrol.route'].sudo().search([], limit=50) if 'security.patrol.route' in env else []
        cats = env['security.task.category'].sudo().search([]) if 'security.task.category' in env else []
        return _ok({
            'is_supervisor': True,
            'teams': [{'id': t.id, 'name': t.name, 'shift': t.shift_type_id.name if t.shift_type_id else None} for t in teams],
            'guards': [{'id': g.id, 'name': g.name} for g in guards],
            'premises': [{'id': p.id, 'name': p.name} for p in prem],
            'routes': [{'id': r.id, 'name': r.name, 'premise': r.premise_id.name if r.premise_id else None} for r in routes],
            'task_categories': [{'id': c.id, 'name': c.name} for c in cats],
            'inspection_types': [('routine', 'روتيني'), ('special', 'خاص'), ('follow_up', 'متابعة'), ('audit', 'تدقيق'), ('incident', 'حادثة')],
            'severities': [('low', 'منخفض'), ('medium', 'متوسط'), ('high', 'عالٍ'), ('critical', 'حرج')],
            'priorities': [('0', 'منخفض'), ('1', 'عادي'), ('2', 'مرتفع'), ('3', 'عاجل')],
            'pass_types': [('personal', 'شخص'), ('vehicle', 'مركبة')],
        })

    # ---- إنشاء مهمة وإسنادها -------------------------------------------
    @route(API + '/security/sup/task/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def task_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_manage(env):
            return _err('غير مصرّح', 403)
        b = _body() or {}
        name = (b.get('name') or '').strip()
        if not name:
            return _err('عنوان المهمة مطلوب', 400)
        T = env['security.task'].sudo()
        cat = b.get('category_id') or (env['security.task.category'].sudo().search([], limit=1).id if 'security.task.category' in env else False)
        if not cat and 'security.task.category' in env:
            cat = env['security.task.category'].sudo().create({'name': 'عام'}).id
        client = b.get('client_id') or (self._default_client(env).id if self._default_client(env) else False)
        vals = {'name': name, 'category_id': cat, 'client_id': client}
        if b.get('assigned_guard_id'):
            vals['assigned_to'] = int(b['assigned_guard_id'])
        if b.get('team_id'):
            vals['team_id'] = int(b['team_id'])
        for k in ('deadline', 'start_date', 'end_date'):
            if b.get(k):
                vals[k] = b[k]
        if b.get('duration'):
            vals['duration'] = float(b['duration'])
        if b.get('priority') is not None:
            vals['priority'] = str(b['priority'])
        if b.get('description') and 'description' in T._fields:
            vals['description'] = b['description']
        try:
            rec = T.create(vals)
        except Exception as e:
            return _err('تعذّر إنشاء المهمة: %s' % e, 400)
        # إشعار المُسنَد إليه
        try:
            if vals.get('assigned_to') and 'care.cafm.notification' in env:
                gu = env['security.guard'].sudo().browse(vals['assigned_to']).user_id
                if gu:
                    env['care.cafm.notification'].sudo().push(gu, '📋 مهمة جديدة', name, ntype='info')
        except Exception:
            pass
        return _ok({'id': rec.id, 'name': rec.name})

    # ---- إنشاء دورية وإسنادها ------------------------------------------
    @route(API + '/security/sup/patrol/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def patrol_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_manage(env):
            return _err('غير مصرّح', 403)
        b = _body() or {}
        if 'security.patrol' not in env:
            return _err('الدوريات غير مفعّلة', 404)
        P = env['security.patrol'].sudo()
        if not b.get('route_id'):
            return _err('المسار مطلوب', 400)
        vals = {'route_id': int(b['route_id']), 'patrol_type': b.get('patrol_type') or 'routine'}
        if b.get('guard_id'):
            vals['guard_id'] = int(b['guard_id'])
        if b.get('team_id'):
            vals['team_id'] = int(b['team_id'])
        if b.get('scheduled_start'):
            vals['scheduled_start'] = b['scheduled_start']
        try:
            rec = P.create(vals)
        except Exception as e:
            return _err('تعذّر إنشاء الدورية: %s' % e, 400)
        try:
            if vals.get('guard_id') and 'care.cafm.notification' in env:
                gu = env['security.guard'].sudo().browse(vals['guard_id']).user_id
                if gu:
                    env['care.cafm.notification'].sudo().push(gu, '🚨 دورية مُسندة', rec.name or 'دورية جديدة', ntype='info')
        except Exception:
            pass
        return _ok({'id': rec.id, 'name': rec.name})

    # ---- إنشاء تصريح دخول (بوابة) --------------------------------------
    @route(API + '/security/sup/gatepass/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def gatepass_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_manage(env):
            return _err('غير مصرّح', 403)
        b = _body() or {}
        if 'security.gate.pass' not in env:
            return _err('التصاريح غير مفعّلة', 404)
        # إنشاء security.contact يطلق خطأً بيئياً مؤجّلاً (حقل project.task.is_closed
        # مفقود يُقيَّم عبر mail thread) — نُنشئ جهة الاتصال بـ SQL لتخطّي mail.
        ctx = {'tracking_disable': True, 'mail_create_nolog': True, 'mail_notrack': True}
        try:
            GP = env['security.gate.pass'].sudo().with_context(**ctx)
            dc = self._default_client(env)
            client = int(b['client_id']) if b.get('client_id') else (dc.id if dc else False)
            today = fields.Date.today()
            # الموقع: من الطلب إن حُدِّد، وإلا الموقع الافتراضي للمشرف
            prem = (env['security.premise'].sudo().browse(int(b['premise_id']))
                    if b.get('premise_id') else self._default_premise(env))
            # الزائر شريك (res.partner) — ننشئه بـ SQL لتخطّي mail thread (يطلق
            # خطأ بيئياً: حقل project.task.is_closed مفقود يُقيَّم عبر التتبّع).
            from odoo import SUPERUSER_ID
            env.cr.execute(
                "INSERT INTO res_partner (name, phone, company_id, active, type, "
                "create_uid, create_date, write_uid, write_date) "
                "VALUES (%s,%s,%s,true,'contact',%s, now() at time zone 'UTC', %s, now() at time zone 'UTC') "
                "RETURNING id",
                (b.get('person_name') or 'زائر', b.get('phone') or None,
                 env.company.id, SUPERUSER_ID, SUPERUSER_ID))
            vid = env.cr.fetchone()[0]
            visitor = env['res.partner'].sudo().browse(vid)
            now = fields.Datetime.now()
            vals = {
                'client_id': client, 'visitor_id': visitor.id,
                'premise_id': prem.id if prem else False,
                'purpose': (b.get('purpose') or 'تصريح دخول').strip(),
                'pass_type': b.get('pass_type') or 'personal',
                'start_date': b.get('start_date') or today,
                'end_date': b.get('end_date') or fields.Date.add(today, days=1),
            }
            # حقول الصلاحية (مطلوبة على مستوى القاعدة)
            for f in ('valid_from', 'valid_until'):
                if f in GP._fields:
                    vals[f] = now if f == 'valid_from' else fields.Datetime.add(now, days=1)
            rec = GP.create(vals)
            env.flush_all()  # نُجبر أي خطأ مؤجّل ليُلتقط هنا لا عند نهاية الطلب
            # تفاصيل الشخص (اختياري — لا يُفشل التصريح إن رُفض نوع الهوية)
            if vals['pass_type'] == 'personal' and b.get('person_name') and 'person_ids' in GP._fields:
                try:
                    pfields = env['security.gate.pass.person'].sudo().fields_get(['id_type'])
                    idsel = [k for k, _ in (pfields.get('id_type', {}).get('selection') or [])]
                    rec.write({'person_ids': [(0, 0, {
                        'name': b['person_name'], 'id_number': b.get('id_number') or '',
                        'id_type': (b.get('id_type') if b.get('id_type') in idsel else (idsel[0] if idsel else False)),
                    })]})
                except Exception:
                    pass
        except Exception as e:
            return _err('تعذّر إنشاء التصريح: %s' % e, 400)
        return _ok({'id': rec.id, 'name': rec.name})

    # ---- حالة نشاط الحارس (heartbeat + عرض للمشرف) ---------------------
    @route(API + '/security/guard/heartbeat', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def guard_heartbeat(self, **kw):
        """نبضة من جهاز الحارس: حركة/نبض قلب/سكون → تحدّث حالته وتعيدها."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        b = _body() or {}
        # تخزين آخر موقع GPS للحارس على سجل security.guard (ليراه الفريق على الخريطة)
        try:
            lat, lng = b.get('lat'), b.get('lng')
            if lat is not None and lng is not None and 'security.guard' in env:
                G = env['security.guard'].sudo()
                g = G.search([('user_id', '=', env.uid)], limit=1)
                if not g:
                    se = env['security.employee'].sudo().search(
                        [('employee_id.user_id', '=', env.uid)], limit=1) if 'security.employee' in env else None
                    if se:
                        g = G.search([('security_employee_id', '=', se.id)], limit=1)
                if g and 'latitude' in g._fields:
                    vals = {'latitude': float(lat), 'longitude': float(lng)}
                    if 'last_update' in g._fields:
                        vals['last_update'] = fields.Datetime.now()
                    if b.get('battery') is not None and 'battery_level' in g._fields:
                        vals['battery_level'] = float(b['battery'])
                    g.write(vals)
        except Exception:
            pass
        if 'care.guard.presence' not in env:
            return _ok({'state': 'active'})
        rec = env['care.guard.presence'].sudo().heartbeat(
            env.user, moving=b.get('moving'), heart_rate=b.get('heart_rate'),
            still=b.get('still'), battery=b.get('battery'))
        return _ok({'state': rec.state})

    @route(API + '/security/sup/presence', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def team_presence(self, **kw):
        """حالة نشاط أعضاء فريق المشرف لحظياً (نشط/سكون/نائم/غير متصل)."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_manage(env):
            return _err('غير مصرّح', 403)
        teams = self._scope_teams(env)
        se = teams.mapped('member_ids')
        guards = env['security.guard'].sudo().search([('security_employee_id', 'in', se.ids)])
        uids = [u for u in guards.mapped('user_id').ids]
        P = env['care.guard.presence'].sudo().search([('user_id', 'in', uids)]) if 'care.guard.presence' in env else []
        if P:
            P._recompute_state()
        pmap = {p.user_id.id: p for p in P}
        cnt = {'active': 0, 'idle': 0, 'sleep': 0, 'offline': 0}
        members = []
        for g in guards:
            p = pmap.get(g.user_id.id) if g.user_id else None
            st = p.state if p else 'offline'
            cnt[st] = cnt.get(st, 0) + 1
            members.append({
                'guard_id': g.id, 'name': g.name, 'state': st,
                'heart_rate': p.heart_rate if p else None,
                'battery': p.battery if p else None,
                'last_seen': str(p.last_seen or '')[:19] if p else None,
            })
        return _ok({'members': members, 'counts': cnt, 'total': len(members)})

    # ---- إشعار الفريق (المشرف يرسل لأعضائه أو لأشخاص محدّدين) ------------
    @route(API + '/security/sup/notify', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def team_notify(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_manage(env):
            return _err('غير مصرّح', 403)
        b = _body() or {}
        msg = (b.get('message') or '').strip()
        if not msg:
            return _err('نص الرسالة مطلوب', 400)
        title = (b.get('title') or '📢 إشعار من المشرف').strip()
        # أهداف: حراس محدّدون أو كل أعضاء فرق المشرف
        users = env['res.users']
        gids = b.get('guard_ids') or []
        if gids:
            guards = env['security.guard'].sudo().browse([int(i) for i in gids]).exists()
            users = guards.mapped('user_id')
        else:
            teams = self._scope_teams(env)
            se = teams.mapped('member_ids')
            guards = env['security.guard'].sudo().search([('security_employee_id', 'in', se.ids)])
            users = guards.mapped('user_id')
        if not users:
            return _err('لا مستلمين', 404)
        try:
            if 'care.cafm.notification' in env:
                env['care.cafm.notification'].sudo().push(users, title, msg, ntype='info')
        except Exception as e:
            return _err('تعذّر الإرسال: %s' % e, 400)
        return _ok({'notified': len(users)})

    # ---- إنشاء سجل تفتيش (متاح للحارس أيضاً) ---------------------------
    @route(API + '/security/sup/inspection/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def inspection_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        # التفتيش متاح لأي حارس (وله guard) أو مشرف أو عميل
        if not (self._my_guard(env) or self._can_manage(env)):
            return _err('غير مصرّح', 403)
        b = _body() or {}
        if 'security.inspection' not in env:
            return _err('التفتيشات غير مفعّلة', 404)
        I = env['security.inspection'].sudo()
        prem = b.get('premise_id') or (self._default_premise(env).id if self._default_premise(env) else False)
        guard = b.get('guard_id') or (self._my_guard(env).id if self._my_guard(env) else False)
        vals = {
            'premise_id': prem, 'guard_id': guard,
            'inspection_type': b.get('inspection_type') or 'routine',
            'issue_type': b.get('issue_type') or 'security',
            'severity': b.get('severity') or 'medium',
            'issue_description': (b.get('issue_description') or b.get('description') or 'تفتيش').strip(),
        }
        if b.get('timestamp'):
            vals['timestamp'] = b['timestamp']
        # حقول تفصيلية إضافية — تُكتب فقط إن كانت موجودة في الموديل
        extra = {
            'area': b.get('area'), 'location': b.get('area'),
            'corrective_action': b.get('corrective_action'),
            'action_required': b.get('corrective_action'),
            'follow_up_date': b.get('follow_up_date'),
        }
        for f, v in extra.items():
            if v and f in I._fields and f not in vals:
                vals[f] = v
        try:
            rec = I.create(vals)
        except Exception as e:
            return _err('تعذّر إنشاء سجل التفتيش: %s' % e, 400)
        return _ok({'id': rec.id, 'name': rec.name})
