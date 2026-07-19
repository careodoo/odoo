# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import http, fields, _
from odoo.http import request


def esc(v):
    return Markup.escape(v if v is not None else '')


# Fallback only. The live colours come from care.cafm.service.color_hex so the
# app, this portal and the client portal cannot drift apart again.
ACCENTS = {
    'cleaning': '#0ea5e9', 'security': '#e11d48', 'agriculture': '#16a34a',
    'facade': '#8b5cf6', 'maintenance': '#f59e0b', 'pest': '#7c3aed',
    'waste': '#16a34a', 'disinfection': '#0ea5a5', 'pool': '#0891b2',
    'watertank': '#0e7a5f', 'valet': '#b45309', 'hospitality': '#8a6d3b',
    'other': '#64748b',
}


def accent_for(service_type):
    """The one colour this service is drawn in, everywhere."""
    try:
        pal = request.env['care.cafm.service'].sudo().palette()
        if service_type in pal:
            return pal[service_type]['color']
    except Exception:
        pass
    return ACCENTS.get(service_type, ACCENTS['other'])


_PAGE = """<!doctype html><html lang="ar" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>__TITLE__ · CAFM</title>
<style>
:root{--ac:__AC__}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{margin:0;background:#0d1826;color:#e9f1fb;font-family:"Segoe UI",Tahoma,system-ui,"Noto Sans Arabic",sans-serif;direction:rtl;padding-bottom:78px}
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
/* --- persistent navigation: every page used to be a dead end with one
       "back" link, so moving sideways meant walking to the launcher --- */
.nav{position:fixed;bottom:0;left:0;right:0;z-index:9;display:flex;
     background:#0f1c2e;border-top:1px solid #294059;padding:6px 4px 8px}
.nav a{flex:1;text-align:center;color:#7f97b4;font-size:9.5px;font-weight:700;padding:4px 2px}
.nav a .i{display:block;font-size:19px;margin-bottom:2px;filter:grayscale(.5);opacity:.75}
.nav a.on{color:var(--ac)}.nav a.on .i{filter:none;opacity:1}
.crumb{font-size:11.5px;color:#9cb2cd;padding:9px 16px 0}
.crumb a{color:#4aa8ff}
.sec{display:flex;align-items:center;justify-content:space-between;margin:17px 0 9px}
.sec h3{font-size:14.5px;font-weight:900}
.sec a{font-size:12px;color:var(--ac);font-weight:800}
.empty{text-align:center;padding:34px 16px;color:#7f97b4}
.empty .i{font-size:42px;opacity:.55;display:block;margin-bottom:8px}
.pager{display:flex;gap:8px;justify-content:center;margin:14px 0 4px}
.pager a,.pager span{padding:7px 13px;border-radius:9px;font-size:12.5px;font-weight:800;
  background:#152438;border:1px solid #294059}
.pager .cur{background:var(--ac);color:#0b1220;border-color:var(--ac)}
.pager .off{opacity:.35}
</style></head><body>
<div class="top"><div><div class="t">__TITLE__</div></div><a class="back" href="__BACK__">↩ رجوع</a></div>
__CRUMB__
<div class="wrap">__BODY__</div>
__NAV__
</body></html>"""


def _csrf():
    return Markup('<input type="hidden" name="csrf_token" value="%s"/>') % request.csrf_token()


def _nav(active=None):
    """The five places anyone actually moves between, chosen by what this user
    is. Rendered on every page so no page is a dead end."""
    env = request.env
    items = [('/cafm/m', '🏠', 'الرئيسية', 'home')]
    emp = env.user.employee_id
    is_staff = env.user.has_group('base.group_system') or env.user.has_group('base.group_erp_manager')
    if emp:
        items += [('/cafm/m/worker', '🧹', 'مهامّي', 'worker'),
                  ('/cafm/m/scan', '▣', 'مسح', 'scan')]
    else:
        items += [('/cafm/m/workorders', '🛠️', 'الأعمال', 'wo'),
                  ('/cafm/m/quality', '🔎', 'ملاحظة', 'quality')]
    if is_staff or emp:
        items.append(('/cafm/m/supervisor', '🦺', 'الإشراف', 'sup'))
    else:
        items.append(('/cafm/m/client', '🧑\u200d💼', 'بوابتي', 'client'))
    unread = 0
    try:
        unread = env['care.cafm.notification'].sudo().search_count(
            [('user_id', '=', env.user.id), ('is_read', '=', False)])
    except Exception:
        pass
    bell = '🔔' if not unread else '🔴'
    items.append(('/cafm/m/inbox', bell, 'الإشعارات%s' % (' (%s)' % unread if unread else ''), 'inbox'))
    out = Markup('<div class="nav">')
    for href, icon, label, key in items:
        out += Markup('<a class="%s" href="%s"><span class="i">%s</span>%s</a>') % (
            'on' if key == active else '', href, icon, esc(label))
    return out + Markup('</div>')


def _crumb(trail):
    """trail: [(label, href_or_None), ...] — the last entry is the current page."""
    if not trail:
        return Markup('')
    out = Markup('<div class="crumb">')
    for i, (label, href) in enumerate(trail):
        if i:
            out += Markup(' › ')
        out += (Markup('<a href="%s">%s</a>') % (href, esc(label))) if href else esc(label)
    return out + Markup('</div>')


def sec(title, more_href=None, more_label='عرض الكل'):
    """A section heading, optionally with a link to the full list."""
    tail = (Markup('<a href="%s">%s ›</a>') % (more_href, esc(more_label))) if more_href else Markup('')
    return Markup('<div class="sec"><h3>%s</h3>%s</div>') % (esc(title), tail)


def empty(text, icon='📭'):
    return Markup('<div class="empty"><span class="i">%s</span>%s</div>') % (icon, esc(text))


def pager(page, pages, url):
    """url must contain a {p} placeholder. Long lists were silently truncated
    at a hard limit with no way to reach the rest."""
    if pages <= 1:
        return Markup('')
    out = Markup('<div class="pager">')
    prev_cls = 'off' if page <= 1 else ''
    out += Markup('<a class="%s" href="%s">‹</a>') % (Markup(prev_cls), url.format(p=max(1, page - 1)))
    for n in range(max(1, page - 2), min(pages, page + 2) + 1):
        out += (Markup('<span class="cur">%s</span>') % n) if n == page else (
            Markup('<a href="%s">%s</a>') % (url.format(p=n), n))
    next_cls = 'off' if page >= pages else ''
    out += Markup('<a class="%s" href="%s">›</a>') % (Markup(next_cls), url.format(p=min(pages, page + 1)))
    return out + Markup('</div>')


def _shell(title, body, accent='#f7a23b', back='/cafm/m', nav=None, crumb=None):
    """Full mobile HTML page shell (RTL, dark, self-contained). Built with
    .replace (not %-format) so literal % in the CSS is safe."""
    page = (_PAGE.replace('__AC__', accent).replace('__BACK__', back)
            .replace('__TITLE__', str(esc(title)))
            .replace('__CRUMB__', str(_crumb(crumb or [])))
            .replace('__NAV__', str(_nav(nav)))
            .replace('__BODY__', str(body)))
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
            ('maint', '🔧', 'الصيانة', 'أعطال · قطع غيار · فحوص'),
            ('valet', '🚗', 'صف السيارات', 'استلام · صفّ · تسليم'),
            ('inbox', '🔔', 'الإشعارات', 'ما وصلني · غير المقروء'),
            ('support', '🎧', 'الدعم الفني', 'تذاكر · متابعة الرد'),
            ('permissions', '🔐', 'صلاحياتي', 'ما يسمح به حسابك'),
        ]
        # hospitality lives on its own route prefix, not /cafm/m/<key>
        extra = [
            ('/hosp', '☕', 'الضيافة', 'اطلب مشروبك بمواصفاتك'),
            ('/hosp/kitchen', '🍳', 'شاشة المطبخ', 'الطلبات لايف'),
            ('/hosp/stats', '📊', 'إحصائيات الضيافة', 'الاستهلاك والتكلفة'),
        ]
        tiles = Markup('').join(Markup(
            '<a class="tile" href="/cafm/m/%s"><div class="i">%s</div><div class="n">%s</div><div class="s">%s</div></a>'
        ) % (a[0], a[1], a[2], a[3]) for a in apps)
        tiles += Markup('').join(Markup(
            '<a class="tile" href="%s"><div class="i">%s</div><div class="n">%s</div><div class="s">%s</div></a>'
        ) % (a[0], a[1], a[2], a[3]) for a in extra)
        body = Markup(
            '<div class="kpi"><div><div class="n">%s</div><div class="l">مهامّي المفتوحة</div></div>'
            '<div><div class="n">%s</div><div class="l">ملاحظات مفتوحة</div></div></div>'
            '<h3 style="margin:16px 0 10px">التطبيقات — حسب دورك</h3>'
            '<div class="grid">%s</div>'
            '<p class="muted" style="margin-top:14px">تطبيق واحد يتكيّف مع كل دور وخدمة. مرحباً %s.</p>'
        ) % (wo_mine, obs_open, tiles, esc(env.user.name))
        return _shell('CAFM', body, back='/web', nav='home')

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
        # A supervisor opens this to place work, so unassigned comes first and
        # the list is long enough to actually clear a backlog.
        WO = env['care.cafm.workorder']
        base = [('state', 'not in', ('done', 'verified', 'cancelled'))]
        unassigned = WO.search(base + [('employee_id', '=', False)], limit=25)
        wos = unassigned | WO.search(
            base + [('employee_id', '!=', False)], limit=max(0, 25 - len(unassigned)))
        obs = env['care.cafm.observation'].search([('state', 'not in', ('closed', 'cancelled'))], limit=6)
        scans = env['care.cafm.scan'].search([], limit=6)
        who = Markup('')
        for s in scans:
            who += Markup('<div class="card row"><div><div class="h4">%s</div>'
                          '<div class="muted">📍 %s</div></div><span class="muted">%s</span></div>'
                          ) % (esc(s.employee_id.sudo().name or '—'), esc(s.location_id.name or '—'),
                               esc(fields.Datetime.to_string(s.scan_datetime)[11:16] if s.scan_datetime else ''))
        if not scans:
            who = Markup('<div class="card muted">لا عمليات مسح بعد.</div>')
        # Crews this supervisor can actually hand work to.
        crew = env['care.cafm.employee'].sudo() if 'care.cafm.employee' in env else None
        workers = env['hr.employee'].sudo().search(
            [('id', 'in', env['care.cafm.team'].sudo().search([]).mapped('member_ids').ids)])
        wo_rows = Markup('')
        for w in wos:
            # hr.employee is private: reading a colleague's record without sudo
            # raises on the restricted HR fields and 403s the whole page.
            assigned = w.employee_id.sudo()
            # This board listed "غير مُسنَد" and then offered no way to fix it —
            # the one thing a supervisor opens this page to do.
            if assigned:
                act = Markup('<div class="muted" style="margin-top:6px">👷 %s</div>') % esc(assigned.name)
            elif workers:
                opts = Markup('').join(
                    Markup('<option value="%s">%s%s</option>') % (
                        e.id, esc(e.name), esc(' — %s' % e.job_title if e.job_title else ''))
                    for e in workers[:200])
                act = Markup(
                    '<form method="post" action="/cafm/m/wo/%s/assign" style="margin-top:8px">%s'
                    '<label>إسناد إلى</label><select name="employee_id" required>%s</select>'
                    '<button class="btn">إسناد المهمة</button></form>'
                ) % (w.id, _csrf(), opts)
            else:
                act = Markup('<div class="muted" style="margin-top:6px">غير مُسنَد</div>')
            wo_rows += Markup('<div class="card"><div class="h4">%s</div>'
                              '<div class="muted">📍 %s · <span class="pill %s">%s</span></div>%s</div>'
                              ) % (esc(w.title), esc(w.location_id.name or '—'),
                                   'crit' if w.is_overdue else 'info',
                                   esc(dict(w._fields['state'].selection).get(w.state)), act)
        body = Markup(
            '<div class="kpi"><div><div class="n">%s</div><div class="l">أوامر مفتوحة</div></div>'
            '<div><div class="n" style="color:%s">%s</div><div class="l">بانتظار الإسناد</div></div>'
            '<div><div class="n">%s</div><div class="l">ملاحظات</div></div></div>'
            '<h3 style="margin:14px 0 10px">من أين الآن؟ (من المسح)</h3>%s'
            '<h3 style="margin:16px 0 10px">أوامر العمل</h3>%s'
            '<a class="btn g" href="/cafm/m/quality">＋ رصد ملاحظة تصحيح</a>'
        ) % (WO.search_count(base), '#f2603f' if unassigned else '#e9f1fb',
             WO.search_count(base + [('employee_id', '=', False)]), len(obs), who, wo_rows)
        return _shell('المشرف', body, ACCENTS['maintenance'], nav='sup')

    @http.route('/cafm/m/wo/<int:wid>/assign', type='http', auth='user',
                methods=['POST'], website=False, csrf=True)
    def wo_assign(self, wid, **post):
        """Hand a work order to a worker straight from the supervisor board."""
        env = request.env
        w = env['care.cafm.workorder'].sudo().browse(wid).exists()
        eid = int(post.get('employee_id') or 0)
        if w and eid:
            w.employee_id = eid
            try:
                w.action_assign()
            except Exception:
                w.state = 'assigned'
        return request.redirect('/cafm/m/supervisor')

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
        return _shell('الجودة', body, ACCENTS['pest'], nav='quality')

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
        # waste portal points to the active source (new CAFM module vs legacy)
        waste_base = '/waste/orders' if env['ir.config_parameter'].sudo().get_param(
            'care.waste.source', 'legacy') == 'cafm' else '/service_orders'
        cards = Markup('')
        for s in svc_secs:
            tm = team_by_type.get(s.service_type)
            sub = (Markup('الفريق %s · <span class="pill ok">نشطة</span>') % tm.member_count) if tm \
                else Markup('<span class="pill ok">متاحة</span>')
            href = (' href="%s"' % waste_base) if s.code == 'waste' else ''
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
            actions += Markup('<a class="btn g" href="%s">♻️ نقل ومعالجة النفايات — طلباتي ورحلاتي ←</a>') % Markup(waste_base)
        if 'shop' in codes:
            actions += Markup('<a class="btn g" href="/cafm/m/order">🛒 مشترياتي — طلب من الكتالوج ←</a>')
        if 'workorders' in codes:
            actions += Markup('<a class="btn g" href="/cafm/m/workorders">🧰 أوامر العمل — القائمة والتفاصيل ←</a>')
        # Invoices are always relevant to a client; approval lives only here.
        inv_pending = env['account.move'].sudo().search_count(
            [('partner_id', 'in', pids), ('move_type', 'in', ('out_invoice', 'out_refund')),
             ('state', '=', 'posted'), ('cafm_client_approval', '=', 'pending')]
        ) if 'cafm_client_approval' in env['account.move']._fields else 0
        inv_badge = (' — %s بانتظار ردّك' % inv_pending) if inv_pending else ''
        actions += Markup('<a class="btn g" href="/cafm/m/invoices">💳 الفواتير%s ←</a>') % esc(inv_badge)
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

    # ==================== client web pages (portal parity) ================
    def _fmt(self, n):
        """Money with a thousands separator, always 3 decimals (KWD)."""
        try:
            return '{:,.3f}'.format(float(n or 0))
        except Exception:
            return str(n)

    @http.route('/cafm/m/invoices', type='http', auth='user', website=False)
    def m_invoices(self, **kw):
        """Client invoices + approve/reject — the one client action with no
        other web path. Same data & guard as the app's /client/invoices."""
        env = request.env
        pids, facs, types, codes, name = self._client_scope(env)
        Move = env['account.move'].sudo()
        moves = Move.search([('partner_id', 'in', pids),
                             ('move_type', 'in', ('out_invoice', 'out_refund')),
                             ('state', '=', 'posted')], order='invoice_date desc, id desc', limit=200)
        pay_lbl = {'not_paid': 'غير مدفوعة', 'in_payment': 'قيد الدفع', 'paid': 'مدفوعة',
                   'partial': 'مدفوعة جزئياً', 'reversed': 'معكوسة'}
        has_appr = 'cafm_client_approval' in Move._fields
        total = sum(moves.mapped('amount_total'))
        residual = sum(moves.mapped('amount_residual'))
        cur = moves[:1].currency_id.name if moves else env.company.currency_id.name
        pending = sum(1 for m in moves if has_appr and m.cafm_client_approval == 'pending')
        body = Markup('<div class="kpi"><div><div class="n">%s</div><div class="l">إجمالي (%s)</div></div>'
                      '<div><div class="n">%s</div><div class="l">المتبقّي</div></div>'
                      '<div><div class="n">%s</div><div class="l">بانتظار ردّك</div></div></div>'
                      ) % (esc(self._fmt(total)), esc(cur), esc(self._fmt(residual)), pending)
        if not moves:
            body += Markup('<div class="card muted" style="margin-top:11px">لا فواتير.</div>')
        for m in moves:
            appr = m.cafm_client_approval if has_appr else 'none'
            appr_pill = {'pending': ('<span class="pill warn">بانتظار ردّك</span>'),
                         'accepted': ('<span class="pill ok">قبلتَها</span>'),
                         'rejected': ('<span class="pill crit">رفضتَها</span>')}.get(appr, '')
            overdue = bool(m.invoice_date_due and m.amount_residual > 0
                           and m.invoice_date_due < fields.Date.today())
            body += Markup(
                '<div class="card stripe" style="margin-top:11px">'
                '<div class="row"><div><b>%s</b><div class="muted">%s%s</div></div>'
                '<div style="text-align:end"><div class="big" style="font-size:19px">%s</div>'
                '<div class="muted">%s %s</div></div></div>'
                '<div class="row" style="margin-top:8px">%s '
                '<span class="pill %s">%s</span>%s</div>'
                '<a class="btn g" style="margin-top:9px" href="/cafm/m/invoice/%s">التفاصيل ←</a>'
                '</div>'
            ) % (esc(m.name), esc(str(m.invoice_date or '')),
                 Markup(' · استحقاق %s') % esc(str(m.invoice_date_due)) if m.invoice_date_due else Markup(''),
                 esc(self._fmt(m.amount_total)), esc(cur),
                 Markup('· متبقٍّ %s') % esc(self._fmt(m.amount_residual)) if m.amount_residual else Markup('مدفوعة'),
                 Markup(appr_pill),
                 'crit' if m.payment_state == 'not_paid' else ('ok' if m.payment_state == 'paid' else 'info'),
                 esc(pay_lbl.get(m.payment_state, m.payment_state)),
                 Markup(' <span class="pill crit">متأخّرة</span>') if overdue else Markup(''),
                 m.id)
        return _shell('الفواتير', body, '#7a1340')

    @http.route('/cafm/m/invoice/<int:mid>', type='http', auth='user', website=False)
    def m_invoice(self, mid, **kw):
        env = request.env
        pids, facs, types, codes, name = self._client_scope(env)
        m = env['account.move'].sudo().browse(int(mid)).exists()
        is_mgr = env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system')
        if not m or (m.partner_id.commercial_partner_id.id not in pids and not is_mgr):
            return request.redirect('/cafm/m/invoices')
        cur = m.currency_id.name
        lines = Markup('')
        for l in m.invoice_line_ids.filtered(lambda x: not x.display_type):
            lines += Markup('<div class="row" style="padding:6px 0;border-top:1px solid #294059">'
                            '<div><b>%s</b><div class="muted">%s × %s</div></div>'
                            '<div style="text-align:end"><b>%s</b></div></div>'
                            ) % (esc(l.name or l.product_id.display_name), esc(self._fmt(l.quantity)),
                                 esc(self._fmt(l.price_unit)), esc(self._fmt(l.price_subtotal)))
        appr = m.cafm_client_approval if 'cafm_client_approval' in m._fields else 'none'
        comment = m.cafm_client_comment if 'cafm_client_comment' in m._fields else False
        body = Markup(
            '<div class="card"><div class="row"><div><h3>%s</h3><div class="muted">%s</div></div>'
            '<div style="text-align:end"><div class="big" style="font-size:22px">%s</div>'
            '<div class="muted">%s</div></div></div></div>'
            '<div class="card"><div class="h4">البنود</div>%s'
            '<div class="row" style="padding-top:9px;margin-top:6px;border-top:2px solid #294059">'
            '<b>الإجمالي</b><b>%s %s</b></div>'
            '<div class="row muted"><span>المتبقّي</span><span>%s</span></div></div>'
        ) % (esc(m.name), esc(str(m.invoice_date or '')), esc(self._fmt(m.amount_total)), esc(cur),
             lines, esc(self._fmt(m.amount_total)), esc(cur), esc(self._fmt(m.amount_residual)))
        # approval block
        if appr == 'accepted':
            body += Markup('<div class="card"><span class="pill ok">✅ قبلتَ هذه الفاتورة</span>%s</div>'
                           ) % (Markup('<div class="muted" style="margin-top:6px">%s</div>') % esc(comment) if comment else Markup(''))
        elif appr == 'rejected':
            body += Markup('<div class="card"><span class="pill crit">✋ رفضتَ هذه الفاتورة</span>%s</div>'
                           ) % (Markup('<div class="muted" style="margin-top:6px">%s</div>') % esc(comment) if comment else Markup(''))
        elif appr == 'pending':
            body += Markup(
                '<form class="card" method="post" action="/cafm/m/invoice/%s/decide">'
                '<input type="hidden" name="csrf_token" value="%s">'
                '<div class="h4">مراجعة الفاتورة</div>'
                '<label>ملاحظات (اختياري)</label><textarea name="comment" rows="2"></textarea>'
                '<button class="btn" name="decision" value="accept">✅ قبول الفاتورة</button>'
                '<button class="btn crit" name="decision" value="reject">✋ رفض الفاتورة</button>'
                '</form>'
            ) % (m.id, request.csrf_token())
        return _shell(m.name or 'فاتورة', body, '#7a1340', back='/cafm/m/invoices')

    @http.route('/cafm/m/invoice/<int:mid>/decide', type='http', auth='user', website=False,
                methods=['POST'], csrf=True)
    def m_invoice_decide(self, mid, decision=None, comment=None, **kw):
        env = request.env
        pids, facs, types, codes, name = self._client_scope(env)
        m = env['account.move'].sudo().browse(int(mid)).exists()
        is_mgr = env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system')
        if not m or (m.partner_id.commercial_partner_id.id not in pids and not is_mgr):
            return request.redirect('/cafm/m/invoices')
        if 'cafm_client_approval' in m._fields and decision in ('accept', 'reject'):
            state = 'accepted' if decision == 'accept' else 'rejected'
            m.write({'cafm_client_approval': state, 'cafm_client_comment': (comment or '').strip() or False,
                     'cafm_client_approval_date': fields.Datetime.now(), 'cafm_needs_resend': False})
            try:
                verb = 'قَبِل' if decision == 'accept' else 'رفض'
                m.message_post(body='%s العميل الفاتورة%s' % (verb, ((': ' + comment) if comment else '.')))
            except Exception:
                pass
        return request.redirect('/cafm/m/invoice/%s' % mid)

    @http.route('/cafm/m/workorders', type='http', auth='user', website=False)
    def m_workorders(self, state='open', page=1, q=None, **kw):
        env = request.env
        pids, facs, types, codes, name = self._client_scope(env)
        WO = env['care.cafm.workorder'].sudo()
        dom = [('facility_id', 'in', facs.ids)]
        if state == 'open':
            dom.append(('state', 'not in', ('done', 'verified', 'cancelled')))
        elif state == 'overdue':
            dom.append(('state', 'not in', ('done', 'verified', 'cancelled')))
        elif state and state != 'all':
            dom.append(('state', '=', state))
        q = (q or '').strip()
        if q:
            dom += ['|', '|', ('title', 'ilike', q), ('name', 'ilike', q),
                    ('description', 'ilike', q)]
        # The list used to stop dead at 200 rows with nothing to say so, and no
        # way to reach row 201.
        PER = 25
        try:
            page = max(1, int(page))
        except (TypeError, ValueError):
            page = 1
        if state == 'overdue':
            allw = WO.search(dom, order='request_datetime desc').filtered('is_overdue')
            total = len(allw)
            wos = allw[(page - 1) * PER: page * PER]
        else:
            total = WO.search_count(dom)
            wos = WO.search(dom, order='request_datetime desc',
                            limit=PER, offset=(page - 1) * PER)
        pages = max(1, (total + PER - 1) // PER)
        state_lbl = dict(WO._fields['state'].selection)
        # filter tabs
        tabs = Markup('')
        for code, lbl in (('open', 'مفتوحة'), ('overdue', 'متأخرة'), ('done', 'منجزة'), ('all', 'الكل')):
            cls = 'pill info' if state == code else 'pill'
            tabs += Markup('<a class="%s" style="margin-inline-end:6px" href="/cafm/m/workorders?state=%s">%s</a>'
                           ) % (Markup(cls), Markup(code), esc(lbl))
        body = Markup('<div class="card"><div class="row"><b>أوامر العمل</b>'
                      '<span class="muted">%s سجل · صفحة %s من %s</span></div>'
                      '<div style="margin-top:9px">%s</div>'
                      '<form method="get" action="/cafm/m/workorders" style="margin-top:9px">'
                      '<input type="hidden" name="state" value="%s"/>'
                      '<input name="q" value="%s" placeholder="ابحث في العنوان أو الرقم…"/>'
                      '</form></div>') % (total, page, pages, tabs, esc(state or 'open'), esc(q))
        if not wos:
            body += empty('لا أوامر عمل في هذا التصنيف.', '🛠️')
        for w in wos:
            sev = ''
            if w.priority == '3':
                sev = '<span class="pill crit">عاجل</span>'
            elif w.priority == '2':
                sev = '<span class="pill warn">مرتفع</span>'
            od = Markup(' <span class="pill crit">متأخر</span>') if w.is_overdue else Markup('')
            body += Markup(
                '<a class="card stripe" style="display:block" href="/cafm/m/workorder/%s">'
                '<div class="row"><div><b>%s</b><div class="muted">%s · %s%s</div></div>'
                '<span class="pill info">%s</span></div>%s%s</a>'
            ) % (w.id, esc(w.title or w.name), esc(w.name), esc(w.facility_id.name or ''),
                 Markup(' · %s') % esc(w.location_id.name) if w.location_id else Markup(''),
                 esc(state_lbl.get(w.state, w.state)),
                 Markup('<div style="margin-top:7px">%s%s</div>') % (Markup(sev), od) if (sev or w.is_overdue) else Markup(''),
                 Markup(''))
        body += pager(page, pages,
                      '/cafm/m/workorders?state=%s&q=%s&page={p}' % (state or 'open', q))
        return _shell('أوامر العمل', body, ACCENTS.get('maintenance', '#f7a23b'))

    @http.route('/cafm/m/workorder/<int:wid>', type='http', auth='user', website=False)
    def m_workorder(self, wid, **kw):
        env = request.env
        pids, facs, types, codes, name = self._client_scope(env)
        w = env['care.cafm.workorder'].sudo().browse(int(wid)).exists()
        is_mgr = env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system')
        if not w or (w.facility_id.id not in facs.ids and not is_mgr):
            return request.redirect('/cafm/m/workorders')
        state_lbl = dict(w._fields['state'].selection)
        rows = Markup('')
        def _kv(k, v):
            return Markup('<div class="row" style="padding:6px 0;border-top:1px solid #294059">'
                          '<span class="muted">%s</span><b>%s</b></div>') % (esc(k), esc(v))
        rows += _kv('المرفق', w.facility_id.name or '—')
        if w.location_id:
            rows += _kv('الموقع', w.location_id.name)
        rows += _kv('الخدمة', w.service_id.name or '—')
        if w.employee_id:
            rows += _kv('المُسنَد إليه', w.employee_id.name)
        rows += _kv('الحالة', state_lbl.get(w.state, w.state))
        if w.request_datetime:
            rows += _kv('وقت الطلب', str(w.request_datetime))
        if w.deadline:
            rows += _kv('الموعد النهائي', str(w.deadline))
        if w.done_datetime:
            rows += _kv('وقت الإنجاز', str(w.done_datetime))
        body = Markup('<div class="card"><h3>%s</h3><div class="muted">%s</div>%s</div>'
                      ) % (esc(w.title or w.name), esc(w.name), rows)
        if w.description:
            body += Markup('<div class="card"><div class="h4">الوصف</div><div class="muted">%s</div></div>'
                           ) % esc(w.description)
        # client verify/rate when the work is done and awaiting the client
        if w.state == 'done':
            body += Markup(
                '<form class="card" method="post" action="/cafm/m/workorder/%s/verify">'
                '<input type="hidden" name="csrf_token" value="%s">'
                '<div class="h4">اعتماد العمل</div>'
                '<label>التقييم (1–5)</label><select name="rating">'
                '<option value="5">★★★★★ ممتاز</option><option value="4">★★★★ جيد جدًا</option>'
                '<option value="3">★★★ جيد</option><option value="2">★★ مقبول</option>'
                '<option value="1">★ ضعيف</option></select>'
                '<label>ملاحظات (اختياري)</label><textarea name="note" rows="2"></textarea>'
                '<button class="btn" name="ok" value="1">✅ اعتماد العمل</button></form>'
            ) % (w.id, request.csrf_token())
        return _shell(w.name or 'أمر عمل', body, ACCENTS.get('maintenance', '#f7a23b'),
                      back='/cafm/m/workorders')

    @http.route('/cafm/m/workorder/<int:wid>/verify', type='http', auth='user', website=False,
                methods=['POST'], csrf=True)
    def m_workorder_verify(self, wid, rating=None, note=None, **kw):
        env = request.env
        pids, facs, types, codes, name = self._client_scope(env)
        w = env['care.cafm.workorder'].sudo().browse(int(wid)).exists()
        is_mgr = env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system')
        if not w or (w.facility_id.id not in facs.ids and not is_mgr):
            return request.redirect('/cafm/m/workorders')
        try:
            vals = {}
            if 'client_rating' in w._fields and rating:
                vals['client_rating'] = str(rating)
            if 'client_note' in w._fields and note:
                vals['client_note'] = note
            if vals:
                w.write(vals)
            if hasattr(w, 'action_verify'):
                w.action_verify()
            elif 'verified' in dict(w._fields['state'].selection):
                w.write({'state': 'verified'})
        except Exception:
            pass
        return request.redirect('/cafm/m/workorder/%s' % wid)

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
.kpi{background:#16273d;border:1px solid #274261;border-radius:13px;padding:14px;text-align:center;display:block;color:inherit;text-decoration:none}
a.kpi:hover{border-color:#4aa8ff;background:#1b3050}
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
 <a class="kpi" href="/cafm/m/workorders?tab=all"><div class="n">%(total)s</div><div class="l">إجمالي الأوامر ›</div></a>
 <a class="kpi" href="/cafm/m/workorders?tab=open"><div class="n" style="color:#4aa8ff">%(open)s</div><div class="l">مفتوحة ›</div></a>
 <a class="kpi" href="/cafm/m/workorders?tab=overdue"><div class="n" style="color:#f2603f">%(overdue)s</div><div class="l">متأخرة SLA ›</div></a>
 <a class="kpi" href="/cafm/m/quality"><div class="n" style="color:#f5b638">%(obs)s</div><div class="l">ملاحظات مفتوحة ›</div></a>
 <a class="kpi" href="/cafm/m/security"><div class="n" style="color:#e5484d">%(inc)s</div><div class="l">بلاغات أمنية ›</div></a>
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
