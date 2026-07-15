# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import http, fields, _
from odoo.http import request


def esc(v):
    return Markup.escape(v if v is not None else '')


ACCENTS = {
    'cleaning': '#2f6df6', 'security': '#e5484d', 'agriculture': '#37c98a',
    'facade': '#38bdf8', 'maintenance': '#f7a23b', 'pest': '#a78bfa',
    'waste': '#8a6d3b', 'disinfection': '#0ea5a5', 'pool': '#0891b2',
    'watertank': '#0e7a5f', 'other': '#64748b',
}


_PAGE = """<!doctype html><html lang="ar" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>__TITLE__ · CAFM</title>
<style>
:root{--ac:__AC__}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{margin:0;background:#0d1826;color:#e9f1fb;font-family:"Segoe UI",Tahoma,system-ui,"Noto Sans Arabic",sans-serif;direction:rtl;padding-bottom:20px}
a{color:inherit;text-decoration:none}
.top{position:sticky;top:0;z-index:5;background:linear-gradient(150deg,var(--ac),#0b1220);padding:14px 16px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 6px 18px -8px rgba(0,0,0,.6)}
.top .t{font-weight:900;font-size:17px}
.wrap{padding:14px}
.card{background:#152438;border:1px solid #294059;border-radius:14px;padding:14px;margin-bottom:11px}
.row{display:flex;justify-content:space-between;align-items:center;gap:10px}
h1,h2,h3{margin:0}
.muted{color:#9cb2cd;font-size:12.5px}
.pill{display:inline-flex;gap:5px;align-items:center;font-size:11px;font-weight:800;padding:3px 9px;border-radius:999px}
.ok{background:rgba(55,201,138,.18);color:#37c98a}.warn{background:rgba(245,182,56,.2);color:#f5b638}
.crit{background:rgba(242,96,63,.2);color:#f2603f}.info{background:rgba(74,168,255,.18);color:#4aa8ff}
.stripe{border-inline-start:4px solid var(--ac);padding-inline-start:11px}
.btn{display:block;width:100%;text-align:center;background:var(--ac);color:#0b1220;font-weight:900;border:none;border-radius:11px;padding:13px;font-size:15px;margin-top:9px;cursor:pointer}
.btn.g{background:#1c3149;color:#e9f1fb;border:1px solid #294059}
.btn.crit{background:linear-gradient(150deg,#e5484d,#a5252a);color:#fff}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.tile{background:#152438;border:1px solid #294059;border-radius:14px;padding:16px;text-align:center}
.tile .i{font-size:30px}.tile .n{font-weight:900;margin-top:6px}.tile .s{font-size:11.5px;color:#9cb2cd}
.big{font-size:32px;font-weight:900;letter-spacing:1px}
.back{font-size:13px;opacity:.9}
.kpi{display:flex;gap:10px}.kpi>div{flex:1;background:#152438;border:1px solid #294059;border-radius:12px;padding:11px;text-align:center}
.kpi .n{font-size:20px;font-weight:900}.kpi .l{font-size:10.5px;color:#9cb2cd}
input,select,textarea{width:100%;background:#0d1826;border:1px solid #294059;color:#e9f1fb;border-radius:10px;padding:10px;font-family:inherit;margin-top:6px}
label{font-size:12.5px;color:#9cb2cd;font-weight:700}
.h4{font-size:14px;font-weight:800;margin:0 0 3px}
</style></head><body>
<div class="top"><div><div class="t">__TITLE__</div></div><a class="back" href="__BACK__">↩ رجوع</a></div>
<div class="wrap">__BODY__</div></body></html>"""


def _shell(title, body, accent='#f7a23b', back='/cafm/m'):
    """Full mobile HTML page shell (RTL, dark, self-contained). Built with
    .replace (not %-format) so literal % in the CSS is safe."""
    page = (_PAGE.replace('__AC__', accent).replace('__BACK__', back)
            .replace('__TITLE__', str(esc(title))).replace('__BODY__', str(body)))
    return Markup(page)


class CafmMobile(http.Controller):

    # ---------------- launcher ----------------
    @http.route('/cafm/m', type='http', auth='user', website=False)
    def home(self, **kw):
        env = request.env
        emp = env.user.employee_id
        wo_mine = env['care.cafm.workorder'].search_count([
            ('employee_id', '=', emp.id), ('state', 'not in', ('done', 'verified', 'cancelled'))]) if emp else 0
        obs_open = env['care.cafm.observation'].search_count([('state', 'not in', ('closed', 'cancelled'))])
        apps = [
            ('worker', '🧹', 'تطبيق العامل', 'مهامّي · مسح · تنفيذ'),
            ('security', '🛡️', 'تطبيق الأمن', 'دوريات · بلاغات · طوارئ'),
            ('agriculture', '🌿', 'تطبيق الزراعة', 'ريّ · مواقع · مهام'),
            ('facade', '🏢', 'تطبيق الواجهات', 'تصاريح · رياح · واجهات'),
            ('supervisor', '🦺', 'تطبيق المشرف', 'الموقع الحيّ · إسناد'),
            ('quality', '🔎', 'مراقب الجودة', 'جولة · ملاحظة تصحيح'),
            ('client', '🧑‍💼', 'بوابة العميل', 'خدماتي · بلاغاتي'),
        ]
        tiles = Markup('').join(Markup(
            '<a class="tile" href="/cafm/m/%s"><div class="i">%s</div><div class="n">%s</div><div class="s">%s</div></a>'
        ) % (a[0], a[1], a[2], a[3]) for a in apps)
        body = Markup(
            '<div class="kpi"><div><div class="n">%s</div><div class="l">مهامّي المفتوحة</div></div>'
            '<div><div class="n">%s</div><div class="l">ملاحظات مفتوحة</div></div></div>'
            '<h3 style="margin:16px 0 10px">التطبيقات — حسب دورك</h3>'
            '<div class="grid">%s</div>'
            '<p class="muted" style="margin-top:14px">تطبيق واحد يتكيّف مع كل دور وخدمة. مرحباً %s.</p>'
        ) % (wo_mine, obs_open, tiles, esc(env.user.name))
        return _shell('CAFM', body, back='/web')

    # ---------------- worker (service-flavoured) ----------------
    @http.route(['/cafm/m/worker', '/cafm/m/agriculture'], type='http', auth='user', website=False)
    def worker(self, **kw):
        env = request.env
        emp = env.user.employee_id
        stype = 'agriculture' if request.httprequest.path.endswith('agriculture') else 'cleaning'
        accent = ACCENTS.get(stype, ACCENTS['cleaning'])
        icon = '🌿' if stype == 'agriculture' else '🧹'
        dom = [('state', 'not in', ('done', 'verified', 'cancelled'))]
        if emp:
            dom.append(('employee_id', '=', emp.id))
        wos = env['care.cafm.workorder'].search(dom, limit=15)
        rows = Markup('')
        for w in wos:
            col = {'3': '#f2603f', '2': '#f5b638', '1': '#4aa8ff', '0': '#37c98a'}.get(w.priority, '#4aa8ff')
            if w.state == 'in_progress':
                act = Markup('<a class="btn ok-btn" style="background:#37c98a;color:#04201c" href="/cafm/m/wo/%s/done">✔ تم — أوقف العدّاد</a>') % w.id
                badge = Markup('<span class="pill info">قيد التنفيذ · العدّاد يعمل</span>')
            else:
                act = Markup('<a class="btn" href="/cafm/m/wo/%s/start">▣ امسح للبدء وإثبات الحضور</a>') % w.id
                badge = Markup('<span class="pill warn">بانتظار البدء</span>')
            rows += Markup(
                '<div class="card stripe" style="border-inline-start-color:%s">'
                '<div class="h4">%s</div>'
                '<div class="muted">📍 %s · %s</div>%s%s</div>'
            ) % (col, esc(w.title), esc(w.location_id.name or '—'),
                 esc(w.facility_id.name or ''), Markup('<div style="margin-top:6px">%s</div>') % badge, act)
        if not wos:
            rows = Markup('<div class="card muted">لا مهامّ مفتوحة الآن ✅</div>')
        extra = Markup('')
        if stype == 'cleaning' and 'care.cafm.clean.round' in env:
            extra = Markup('<a class="btn g" href="/cafm/m/clean">🧹 تطبيق النظافة — جولات · جداول · تدقيق ←</a>')
        elif stype == 'agriculture' and 'care.cafm.agri.zone' in env:
            extra = Markup('<a class="btn g" href="/cafm/m/agri">🌿 تطبيق الزراعة — ريّ · نباتات · معالجات ←</a>')
        body = Markup('<div class="kpi"><div><div class="n">%s</div><div class="l">مهامّي</div></div>'
                      '<div><div class="n">%s</div><div class="l">%s</div></div></div>%s'
                      '<h3 style="margin:14px 0 10px">%s مهامّي اليوم</h3>%s') % (
            len(wos), icon, 'خدمة', extra, icon, rows)
        return _shell('العامل', body, accent)

    # ---------------- SECURITY (rich) ----------------
    @http.route('/cafm/m/security', type='http', auth='user', website=False)
    def security(self, **kw):
        env = request.env
        accent = ACCENTS['security']
        points = env['care.cafm.location'].search([('is_checkpoint', '=', True)], limit=8)
        # recent incidents = observations (security) or critical obs
        incs = env['care.cafm.observation'].search(
            [('state', 'not in', ('closed', 'cancelled'))], limit=6)
        # coverage: checkpoints scanned today
        today = fields.Date.today()
        scans = env['care.cafm.scan'].search([('scan_type', '=', 'patrol')], limit=1)
        pt_rows = Markup('')
        for p in points:
            last = p.last_scan_id
            done = last and last.scan_datetime and last.scan_datetime.date() == today
            pt_rows += Markup(
                '<div class="card row"><div><div class="h4">%s</div><div class="muted">%s</div></div>'
                '<a class="pill %s" href="/cafm/m/scan?code=%s&type=patrol">%s</a></div>'
            ) % (esc(p.name), esc(p.facility_id.name or ''),
                 'ok' if done else 'warn', esc(p.code),
                 Markup('مُسحت ✔') if done else Markup('▣ امسح'))
        if not points:
            pt_rows = Markup('<div class="card muted">لا نقاط دورية معرّفة بعد.</div>')
        inc_rows = Markup('')
        for i in incs:
            sc = {'critical': 'crit', 'high': 'crit', 'medium': 'warn', 'low': 'info'}.get(i.severity, 'info')
            inc_rows += Markup('<div class="card stripe" style="border-inline-start-color:%s">'
                               '<div class="h4">%s</div><div class="muted">📍 %s · <span class="pill %s">%s</span></div></div>'
                               ) % (ACCENTS['security'], esc(i.title), esc(i.location_id.name or '—'), sc,
                                    esc(dict(i._fields['severity'].selection).get(i.severity)))
        if not incs:
            inc_rows = Markup('<div class="card muted">لا بلاغات مفتوحة.</div>')
        body = Markup(
            '<div class="card" style="background:linear-gradient(150deg,#1c2333,#152438)">'
            '<div class="row"><div><div class="h4">نقطتي: البوابة الرئيسية</div>'
            '<div class="muted">حضور بصمة ✔ · وردية صباحية</div></div>'
            '<span class="pill ok">على رأس العمل</span></div></div>'
            '<a class="btn" href="/cafm/m/sec">🛡️ التطبيق الأمني الكامل — دوريات · بلاغات · تصاريح · مفاتيح ←</a>'
            '<a class="btn crit" href="/cafm/m/panic">🚨 زر الطوارئ / بلاغ فوري</a>'
            '<h3 style="margin:16px 0 10px">نقاط الدورية (امسح QR)</h3>%s'
            '<h3 style="margin:16px 0 10px">البلاغات المفتوحة</h3>%s'
            '<a class="btn g" href="/cafm/m/quality">＋ تسجيل بلاغ/ملاحظة</a>'
        ) % (pt_rows, inc_rows)
        return _shell('الأمن', body, accent)

    @http.route('/cafm/m/panic', type='http', auth='user', website=False)
    def panic(self, **kw):
        env = request.env
        fac = env['care.cafm.facility'].search([], limit=1)
        env['care.cafm.observation'].create({
            'title': _('🚨 بلاغ طوارئ من فرد الأمن'), 'facility_id': fac.id if fac else False,
            'severity': 'critical', 'description': _('بلاغ فوري عبر زر الطوارئ.')})
        body = Markup('<div class="card"><div class="big" style="color:#f2603f">🚨 أُرسل البلاغ</div>'
                      '<p class="muted">وصل غرفة القيادة والمشرف فوراً. ابقَ آمناً.</p></div>'
                      '<a class="btn" href="/cafm/m/security">عودة لتطبيق الأمن</a>')
        return _shell('طوارئ', body, ACCENTS['security'])

    # ---------------- supervisor ----------------
    @http.route('/cafm/m/supervisor', type='http', auth='user', website=False)
    def supervisor(self, **kw):
        env = request.env
        wos = env['care.cafm.workorder'].search(
            [('state', 'not in', ('done', 'verified', 'cancelled'))], limit=10)
        obs = env['care.cafm.observation'].search([('state', 'not in', ('closed', 'cancelled'))], limit=6)
        scans = env['care.cafm.scan'].search([], limit=6)
        who = Markup('')
        for s in scans:
            who += Markup('<div class="card row"><div><div class="h4">%s</div>'
                          '<div class="muted">📍 %s</div></div><span class="muted">%s</span></div>'
                          ) % (esc(s.employee_id.name or '—'), esc(s.location_id.name or '—'),
                               esc(fields.Datetime.to_string(s.scan_datetime)[11:16] if s.scan_datetime else ''))
        if not scans:
            who = Markup('<div class="card muted">لا عمليات مسح بعد.</div>')
        wo_rows = Markup('')
        for w in wos:
            wo_rows += Markup('<div class="card"><div class="h4">%s</div>'
                              '<div class="muted">📍 %s · 👷 %s · <span class="pill %s">%s</span></div></div>'
                              ) % (esc(w.title), esc(w.location_id.name or '—'),
                                   esc(w.employee_id.name or 'غير مُسنَد'),
                                   'crit' if w.is_overdue else 'info',
                                   esc(dict(w._fields['state'].selection).get(w.state)))
        body = Markup(
            '<div class="kpi"><div><div class="n">%s</div><div class="l">أوامر مفتوحة</div></div>'
            '<div><div class="n">%s</div><div class="l">ملاحظات</div></div></div>'
            '<h3 style="margin:14px 0 10px">من أين الآن؟ (من المسح)</h3>%s'
            '<h3 style="margin:16px 0 10px">أوامر العمل</h3>%s'
            '<a class="btn g" href="/cafm/m/quality">＋ رصد ملاحظة تصحيح</a>'
        ) % (len(wos), len(obs), who, wo_rows)
        return _shell('المشرف', body, ACCENTS['maintenance'])

    # ---------------- quality: raise observation ----------------
    @http.route('/cafm/m/quality', type='http', auth='user', website=False)
    def quality(self, **kw):
        env = request.env
        facs = env['care.cafm.facility'].search([])
        svcs = env['care.cafm.service'].search([])
        fopts = Markup('').join(Markup('<option value="%s">%s</option>') % (f.id, esc(f.name)) for f in facs)
        sopts = Markup('').join(Markup('<option value="%s">%s</option>') % (s.id, esc(s.name)) for s in svcs)
        body = Markup(
            '<form method="post" action="/cafm/m/obs/new">'
            '<input type="hidden" name="csrf_token" value="%s"/>'
            '<div class="card"><label>الملاحظة</label><input name="title" required placeholder="مثال: بقع على الأرضية"/>'
            '<label style="margin-top:8px">المرفق</label><select name="facility_id">%s</select>'
            '<label style="margin-top:8px">الخدمة</label><select name="service_id">%s</select>'
            '<label style="margin-top:8px">الخطورة</label><select name="severity">'
            '<option value="low">منخفضة</option><option value="medium" selected>متوسطة</option>'
            '<option value="high">عالية</option><option value="critical">حرجة</option></select>'
            '<label style="margin-top:8px">الوصف</label><textarea name="description" rows="2"></textarea>'
            '<button class="btn" type="submit">＋ تسجيل الملاحظة</button></div></form>'
        ) % (esc(request.csrf_token()), fopts, sopts)
        return _shell('الجودة', body, ACCENTS['pest'])

    @http.route('/cafm/m/obs/new', type='http', auth='user', website=False, methods=['POST'], csrf=True)
    def obs_new(self, **post):
        env = request.env
        env['care.cafm.observation'].create({
            'title': post.get('title') or _('ملاحظة'),
            'facility_id': int(post['facility_id']) if post.get('facility_id') else False,
            'service_id': int(post['service_id']) if post.get('service_id') else False,
            'severity': post.get('severity') or 'medium',
            'description': post.get('description'),
        })
        body = Markup('<div class="card"><div class="big" style="color:#37c98a">✔ سُجّلت الملاحظة</div>'
                      '<p class="muted">ستظهر لدى المشرف لإسنادها بموعد ومسؤول.</p></div>'
                      '<a class="btn" href="/cafm/m/quality">＋ ملاحظة أخرى</a>'
                      '<a class="btn g" href="/cafm/m">الرئيسية</a>')
        return _shell('تم', body, ACCENTS['pest'])

    # ---------------- client portal home ----------------
    def _client_scope(self, env):
        """Resolve a client portal user → (partner_ids, facilities, service
        types, visible section codes, display name). Mirrors the app's
        /client/sections so the portal shows exactly the same menus. Scopes via
        care.cafm.client membership (a sub-user's own partner is often not the
        company that owns the records)."""
        user = env.user
        Section = env['care.cafm.portal.section'].sudo()
        is_mgr = user.has_group('base.group_erp_manager') or user.has_group('base.group_system')
        pids = {user.partner_id.id}
        if user.partner_id.commercial_partner_id:
            pids.add(user.partner_id.commercial_partner_id.id)
        clients = env['care.cafm.client'].sudo().search([('user_ids', 'in', [user.id])])
        for cp in clients.mapped('partner_id'):
            pids.add(cp.id)
            pids.update(env['res.partner'].sudo().search([('commercial_partner_id', '=', cp.id)]).ids)
        facs = env['care.cafm.facility'].sudo().search([('partner_id', 'in', list(pids))])
        types = set()
        for tm in env['care.cafm.team'].sudo().search([('facility_id', 'in', facs.ids)]):
            if tm.service_id.service_type:
                types.add(tm.service_id.service_type)
        if is_mgr:
            codes = set(Section.search([]).mapped('code'))
        elif clients:
            codes = set()
            for c in clients:
                codes |= c.visible_section_codes(types)
        else:
            codes = Section.auto_codes_for_types(types)
        name = clients[:1].partner_id.name if clients else (facs[:1].partner_id.name if facs else user.name)
        return list(pids), facs, types, codes, name

    @http.route('/cafm/m/client', type='http', auth='user', website=False)
    def client(self, **kw):
        env = request.env
        pids, facs, types, codes, name = self._client_scope(env)
        Section = env['care.cafm.portal.section'].sudo()
        # only the service sections this client may see (respects auto/custom mode)
        svc_secs = Section.search([('code', 'in', list(codes)), ('is_service', '=', True)], order='sequence')
        teams = env['care.cafm.team'].sudo().search([('facility_id', 'in', facs.ids)])
        team_by_type = {}
        for tm in teams:
            if tm.service_id.service_type:
                team_by_type.setdefault(tm.service_id.service_type, tm)
        cards = Markup('')
        for s in svc_secs:
            tm = team_by_type.get(s.service_type)
            sub = (Markup('الفريق %s · <span class="pill ok">نشطة</span>') % tm.member_count) if tm \
                else Markup('<span class="pill ok">متاحة</span>')
            href = ' href="/service_orders"' if s.code == 'waste' else ''
            tag = 'a' if href else 'div'
            cards += Markup('<%s class="tile"%s><div class="i">%s</div><div class="n">%s</div><div class="s">%s</div></%s>'
                            ) % (Markup(tag), Markup(href), esc(s.icon or '🧩'), esc(s.name), sub, Markup(tag))
        if not cards:
            cards = Markup('<div class="card muted">لا خدمات معرّفة بعد.</div>')
        wo_open = env['care.cafm.workorder'].sudo().search_count(
            [('facility_id', 'in', facs.ids), ('state', 'not in', ('done', 'verified', 'cancelled'))]) if 'workorders' in codes else 0
        # action buttons — gated by section visibility
        actions = Markup('')
        if 'waste' in codes:
            actions += Markup('<a class="btn g" href="/service_orders">♻️ نقل ومعالجة النفايات — طلباتي ورحلاتي ←</a>')
        if 'shop' in codes:
            actions += Markup('<a class="btn g" href="/cafm/m/order">🛒 مشترياتي — طلب من الكتالوج ←</a>')
        if 'workorders' in codes:
            actions += Markup('<a class="btn" href="/cafm/m/quality">＋ طلب خدمة / بلاغ</a>')
        kpi = Markup('')
        if 'workorders' in codes:
            kpi = Markup('<div class="kpi" style="margin-top:12px"><div><div class="n">%s</div>'
                         '<div class="l">بلاغات مفتوحة</div></div>'
                         '<div><div class="n">★4.6</div><div class="l">تقييمكم</div></div></div>') % wo_open
        body = Markup(
            '<div class="card"><div class="h4">%s</div><div class="muted">الخدمات المقدّمة لكم</div></div>'
            '<div class="grid">%s</div>%s%s'
        ) % (esc(name or 'عميلنا الكريم'), cards, kpi, actions)
        return _shell('بوابة العميل', body, ACCENTS['disinfection'])

    # ---------------- actions: scan / start / done ----------------
    @http.route('/cafm/m/scan', type='http', auth='user', website=False)
    def scan(self, code=None, type='move', **kw):
        env = request.env
        loc = env['care.cafm.location'].search([('code', '=', code)], limit=1) if code else False
        emp = env.user.employee_id
        if loc:
            env['care.cafm.scan'].create({
                'employee_id': emp.id if emp else False, 'location_id': loc.id, 'scan_type': type})
        msg = (_('تم تسجيل موقعك: %s') % loc.name) if loc else _('رمز غير معروف')
        body = Markup('<div class="card"><div class="big" style="color:#37c98a">▣ %s</div>'
                      '<p class="muted">%s</p></div>'
                      '<a class="btn g" href="/cafm/m/security">عودة</a>') % (
            Markup('تم المسح') if loc else Markup('خطأ'), esc(msg))
        return _shell('مسح', body, '#2dd4bf')

    @http.route('/cafm/m/wo/<int:wid>/<string:act>', type='http', auth='user', website=False)
    def wo_action(self, wid, act, **kw):
        env = request.env
        wo = env['care.cafm.workorder'].browse(wid)
        if wo.exists():
            if act == 'start':
                wo.action_scan_start()
            elif act == 'done':
                wo.action_done()
        return request.redirect('/cafm/m/worker')


def _bar(label, val, total, color='#f7a23b'):
    pct = (100.0 * val / total) if total else 0
    return Markup(
        '<div style="display:grid;grid-template-columns:130px 1fr 44px;align-items:center;gap:10px;font-size:12.5px;margin:6px 0">'
        '<span>%s</span><div style="height:9px;border-radius:5px;background:#26364d;overflow:hidden">'
        '<div style="height:100%%;width:%.0f%%;background:%s;border-radius:5px"></div></div>'
        '<span style="text-align:left;font-weight:700">%s</span></div>'
    ) % (esc(label), pct, color, val)


class CafmDashboard(http.Controller):

    @http.route('/cafm/dashboard', type='http', auth='user', website=False)
    def dashboard(self, **kw):
        env = request.env
        WO = env['care.cafm.workorder']
        total = WO.search_count([])
        open_wo = WO.search_count([('state', 'not in', ('done', 'verified', 'cancelled'))])
        overdue = WO.search_count([('is_overdue', '=', True)])
        done = WO.search([('state', 'in', ('done', 'verified')), ('done_datetime', '!=', False),
                          ('deadline', '!=', False)])
        in_sla = done.filtered(lambda w: w.done_datetime <= w.deadline)
        sla = (100.0 * len(in_sla) / len(done)) if done else 100.0
        obs_open = env['care.cafm.observation'].search_count([('state', 'not in', ('closed', 'cancelled'))])
        inc_open = env['security.incident.report'].sudo().search_count([('state', 'not in', ('closed', 'resolved'))]) if 'security.incident.report' in env else 0
        facilities = env['care.cafm.facility'].search([])
        services = env['care.cafm.service'].search([])

        # by state
        state_lbl = dict(WO._fields['state'].selection)
        by_state = Markup('')
        for st, lbl in [('new', ''), ('assigned', ''), ('in_progress', ''), ('done', ''), ('verified', '')]:
            c = WO.search_count([('state', '=', st)])
            by_state += _bar(state_lbl.get(st, st), c, total, '#4aa8ff')
        # by service
        by_svc = Markup('')
        for s in services:
            c = WO.search_count([('service_id', '=', s.id)])
            by_svc += _bar((s.icon or '') + ' ' + s.name, c, total or 1, ACCENTS.get(s.service_type, '#f7a23b'))
        # facilities table
        frows = Markup('')
        for f in facilities:
            col = '#37c98a' if f.sla_compliance >= 90 else ('#f5b638' if f.sla_compliance >= 75 else '#f2603f')
            frows += Markup(
                '<tr><td style="padding:8px 10px;border-bottom:1px solid #26364d">%s</td>'
                '<td style="padding:8px 10px;border-bottom:1px solid #26364d;text-align:center;color:%s;font-weight:800">%.0f%%</td>'
                '<td style="padding:8px 10px;border-bottom:1px solid #26364d;text-align:center">%s</td>'
                '<td style="padding:8px 10px;border-bottom:1px solid #26364d;text-align:center">%s</td></tr>'
            ) % (esc(f.name), col, f.sla_compliance,
                 WO.search_count([('facility_id', '=', f.id), ('state', 'not in', ('done', 'verified', 'cancelled'))]),
                 f.wo_overdue_count)
        # recent feed
        feed = Markup('')
        for o in env['care.cafm.observation'].search([], limit=6):
            sc = {'critical': '#f2603f', 'high': '#f2603f', 'medium': '#f5b638'}.get(o.severity, '#4aa8ff')
            feed += Markup('<div style="border-inline-start:3px solid %s;padding-inline-start:10px;margin:8px 0;font-size:12.5px">'
                           '<b>%s</b><div style="color:#9cb2cd;font-size:11.5px">📍 %s · %s</div></div>'
                           ) % (sc, esc(o.title), esc(o.location_id.name or '—'),
                                esc(dict(o._fields['state'].selection).get(o.state)))

        ring = ('#37c98a' if sla >= 90 else '#f5b638' if sla >= 75 else '#f2603f')
        page = ("""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>غرفة قيادة CAFM</title>
<style>body{margin:0;background:#0d1826;color:#e9f1fb;font-family:"Segoe UI",Tahoma,system-ui,"Noto Sans Arabic",sans-serif;direction:rtl}
.top{background:linear-gradient(135deg,#1e5eff,#0b3ec9);padding:18px 22px;font-weight:900;font-size:20px;display:flex;justify-content:space-between;align-items:center}
.top a{color:#dbe7ff;font-size:13px;text-decoration:none}
.wrap{max-width:1080px;margin:0 auto;padding:18px}
.kpis{display:grid;grid-template-columns:repeat(6,1fr);gap:12px}
@media(max-width:900px){.kpis{grid-template-columns:repeat(3,1fr)}}@media(max-width:560px){.kpis{grid-template-columns:repeat(2,1fr)}}
.kpi{background:#16273d;border:1px solid #274261;border-radius:13px;padding:14px;text-align:center}
.kpi .n{font-size:26px;font-weight:900}.kpi .l{font-size:11px;color:#9cb2cd;margin-top:2px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px}
@media(max-width:820px){.grid{grid-template-columns:1fr}}
.card{background:#16273d;border:1px solid #274261;border-radius:14px;padding:16px}
.card h3{margin:0 0 10px;font-size:15px}
table{width:100%%;border-collapse:collapse;font-size:12.5px}
th{text-align:right;color:#9cb2cd;font-size:11.5px;padding:6px 10px;border-bottom:1px solid #274261}
</style></head><body>
<div class="top"><div>🏗️ غرفة قيادة CAFM</div><a href="/cafm/m">📱 التطبيق</a></div>
<div class="wrap">
<div class="kpis">
 <div class="kpi"><div class="n" style="color:%(ring)s">%(sla).0f%%</div><div class="l">التزام SLA</div></div>
 <div class="kpi"><div class="n">%(total)s</div><div class="l">إجمالي الأوامر</div></div>
 <div class="kpi"><div class="n" style="color:#4aa8ff">%(open)s</div><div class="l">مفتوحة</div></div>
 <div class="kpi"><div class="n" style="color:#f2603f">%(overdue)s</div><div class="l">متأخرة SLA</div></div>
 <div class="kpi"><div class="n" style="color:#f5b638">%(obs)s</div><div class="l">ملاحظات مفتوحة</div></div>
 <div class="kpi"><div class="n" style="color:#e5484d">%(inc)s</div><div class="l">بلاغات أمنية</div></div>
</div>
<div class="grid">
 <div class="card"><h3>أوامر العمل حسب الحالة</h3>%(by_state)s</div>
 <div class="card"><h3>أوامر العمل حسب الخدمة</h3>%(by_svc)s</div>
</div>
<div class="grid">
 <div class="card"><h3>أداء المرافق</h3><table><tr><th>المرفق</th><th style="text-align:center">SLA</th><th style="text-align:center">مفتوحة</th><th style="text-align:center">متأخرة</th></tr>%(frows)s</table></div>
 <div class="card"><h3>أحدث الملاحظات</h3>%(feed)s</div>
</div>
</div></body></html>""") % {
            'ring': ring, 'sla': sla, 'total': total, 'open': open_wo, 'overdue': overdue,
            'obs': obs_open, 'inc': inc_open, 'by_state': by_state, 'by_svc': by_svc,
            'frows': frows, 'feed': feed}
        return request.make_response(page, headers=[('Content-Type', 'text/html; charset=utf-8')])
