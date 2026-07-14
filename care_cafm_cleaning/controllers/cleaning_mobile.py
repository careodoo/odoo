# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import http, fields, _
from odoo.http import request
from odoo.addons.care_cafm.controllers.main import _shell, ACCENTS, esc

CLN = ACCENTS['cleaning']


class CafmCleaningMobile(http.Controller):

    @http.route('/cafm/m/clean', type='http', auth='user', website=False)
    def clean_home(self, **kw):
        env = request.env
        due = env['care.cafm.clean.schedule'].search([('is_due', '=', True)], limit=10)
        rounds = env['care.cafm.clean.round'].search([('state', '=', 'open')], limit=6)
        audits = env['care.cafm.clean.audit'].search([], limit=4)
        # active rounds -> scan out
        rrows = Markup('')
        for r in rounds:
            rrows += Markup('<div class="card row"><div><div class="h4">🧹 %s</div>'
                            '<div class="muted">جارية · دخول %s</div></div>'
                            '<a class="pill info" href="/cafm/m/clean/round/%s/out">▣ خروج</a></div>'
                            ) % (esc(r.location_id.name), esc(str(r.scan_in_time or '')[11:16]), r.id)
        # due areas -> start round
        drows = Markup('')
        for s in due:
            tag = Markup('<span class="pill warn">حسب الطلب</span>') if s.demand_based else Markup('<span class="pill warn">مستحق</span>')
            drows += Markup('<div class="card row"><div><div class="h4">%s</div>'
                            '<div class="muted">%s · %s</div></div>'
                            '<a class="pill ok" href="/cafm/m/clean/start?loc=%s">▶ بدء</a></div>'
                            ) % (esc(s.location_id.name), esc(dict(s._fields['frequency'].selection).get(s.frequency)), tag, s.location_id.id)
        if not due:
            drows = Markup('<div class="card muted">لا مناطق مستحقّة الآن ✅</div>')
        arows = Markup('')
        for a in audits:
            sc = 'ok' if a.score >= 75 else ('warn' if a.score >= 60 else 'crit')
            arows += Markup('<div class="card row"><div><div class="h4">%s</div>'
                            '<div class="muted">%s</div></div><span class="pill %s">%.0f%%</span></div>'
                            ) % (esc(a.location_id.name or a.name), esc(a.name), sc, a.score)
        body = Markup(
            '<div class="kpi"><div><div class="n">%s</div><div class="l">مناطق مستحقّة</div></div>'
            '<div><div class="n">%s</div><div class="l">جولات جارية</div></div></div>'
            '%s'
            '<h3 style="margin:14px 0 10px">مناطق تحتاج تنظيفاً</h3>%s'
            '<a class="btn g" href="/cafm/m/clean/audit">🔎 تدقيق جودة</a>'
            '<h3 style="margin:16px 0 10px">آخر التدقيقات</h3>%s'
        ) % (len(due), len(rounds), rrows, drows, arows)
        return _shell('النظافة', body, CLN)

    @http.route('/cafm/m/clean/start', type='http', auth='user', website=False)
    def clean_start(self, loc=None, **kw):
        env = request.env
        emp = env.user.employee_id
        if loc:
            r = env['care.cafm.clean.round'].create({
                'worker_id': emp.id if emp else False, 'location_id': int(loc)})
            r.action_scan_in()
        return request.redirect('/cafm/m/clean')

    @http.route('/cafm/m/clean/round/<int:rid>/out', type='http', auth='user', website=False)
    def clean_out(self, rid, **kw):
        r = request.env['care.cafm.clean.round'].browse(rid)
        if r.exists():
            r.action_scan_out()
        return request.redirect('/cafm/m/clean')

    @http.route('/cafm/m/clean/audit', type='http', auth='user', website=False)
    def clean_audit(self, **kw):
        env = request.env
        audits = env['care.cafm.clean.audit'].search([], limit=10)
        rows = Markup('')
        for a in audits:
            sc = 'ok' if a.score >= 75 else ('warn' if a.score >= 60 else 'crit')
            rows += Markup('<div class="card"><div class="h4">%s · %s</div>'
                           '<div class="muted">%s · <span class="pill %s">%.0f%% (%s)</span> · %s مخالفة</div></div>'
                           ) % (esc(a.location_id.name or ''), esc(a.name),
                                esc(str(a.audit_date or '')[:16]), sc, a.score,
                                esc(dict(a._fields['rating'].selection).get(a.rating) or ''), a.fail_count)
        if not audits:
            rows = Markup('<div class="card muted">لا تدقيقات بعد — أنشئها من الباك-إند.</div>')
        body = Markup('<p class="muted">تدقيق الجودة يُنشئ ملاحظات تصحيح تلقائياً للبنود المخالفة.</p>%s') % rows
        return _shell('تدقيق النظافة', body, CLN, back='/cafm/m/clean')
