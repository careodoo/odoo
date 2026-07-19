# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import http, fields, _
from odoo.http import request
from odoo.addons.care_cafm.controllers.main import _shell, ACCENTS, esc, _csrf

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
            rows = Markup('<div class="card muted">لا تدقيقات بعد.</div>')
        # This page used to tell the auditor to go and use the backend. The
        # audit is the cleaning QA loop; it belongs where the auditor is.
        body = self._new_audit_form()
        body += Markup('<p class="muted">تدقيق الجودة يُنشئ ملاحظات تصحيح تلقائياً '
                       'للبنود المخالفة.</p>%s') % rows
        return _shell('تدقيق النظافة', body, CLN, back='/cafm/m/clean')

    def _new_audit_form(self):
        env = request.env
        facs = env['care.cafm.facility'].sudo().search([], limit=50)
        if not facs:
            return Markup('')
        tpls = env['care.cafm.clean.audit.template'].sudo().search([])
        fopts = Markup('').join(
            Markup('<option value="%s">%s</option>') % (f.id, esc(f.name)) for f in facs)
        topts = Markup('<option value="">— بنود افتراضية —</option>') + Markup('').join(
            Markup('<option value="%s">%s</option>') % (t.id, esc(t.name)) for t in tpls)
        locs = env['care.cafm.location'].sudo().search(
            [('facility_id', 'in', facs.ids)], limit=300)
        lopts = Markup('<option value="">— بدون موقع محدّد —</option>') + Markup('').join(
            Markup('<option value="%s">%s — %s</option>') % (l.id, esc(l.name),
                                                             esc(l.facility_id.name or ''))
            for l in locs)
        return Markup(
            '<details class="card"><summary style="font-weight:900;cursor:pointer">'
            '📋 بدء تدقيق جديد</summary>'
            '<form method="post" action="/cafm/m/clean/audit/new" style="margin-top:10px">%s'
            '<label>المرفق</label><select name="facility_id" required>%s</select>'
            '<label>الموقع</label><select name="location_id">%s</select>'
            '<label>قالب الفحص</label><select name="template_id">%s</select>'
            '<button class="btn">ابدأ التدقيق</button></form></details>'
        ) % (_csrf(), fopts, lopts, topts)

    # ---- perform the audit, item by item ----
    DEFAULT_ITEMS = [
        ('نظافة الأرضيات', 2), ('نظافة دورات المياه', 3), ('تعبئة المستلزمات', 2),
        ('تفريغ سلال النفايات', 2), ('نظافة الزجاج والمرايا', 1),
        ('تعقيم أسطح التلامس', 3), ('ترتيب المعدّات ووضوح لوحات التحذير', 1),
    ]

    @http.route('/cafm/m/clean/audit/new', type='http', auth='user',
                methods=['POST'], website=False, csrf=True)
    def audit_new(self, **post):
        env = request.env
        fid = int(post.get('facility_id') or 0)
        if not fid:
            return request.redirect('/cafm/m/clean/audit')
        tpl = env['care.cafm.clean.audit.template'].sudo().browse(
            int(post['template_id'])) if post.get('template_id') else None
        items = [(i.name, i.weight) for i in tpl.item_ids] if (tpl and tpl.exists()
                 and getattr(tpl, 'item_ids', False)) else self.DEFAULT_ITEMS
        audit = env['care.cafm.clean.audit'].sudo().create({
            'facility_id': fid,
            'location_id': int(post['location_id']) if post.get('location_id') else False,
            'template_id': tpl.id if (tpl and tpl.exists()) else False,
            'auditor_id': env.user.id,
            'line_ids': [(0, 0, {'name': n, 'weight': w, 'result': 'pass'}) for n, w in items],
        })
        return request.redirect('/cafm/m/clean/audit/%s' % audit.id)

    @http.route('/cafm/m/clean/audit/<int:aid>', type='http', auth='user', website=False)
    def audit_detail(self, aid, **kw):
        env = request.env
        a = env['care.cafm.clean.audit'].sudo().browse(aid).exists()
        if not a:
            return request.redirect('/cafm/m/clean/audit')
        rows = Markup('')
        for l in a.line_ids:
            opts = Markup('')
            for val, label in l._fields['result'].selection:
                sel = ' selected' if l.result == val else ''
                opts += Markup('<option value="%s"%s>%s</option>') % (val, Markup(sel), esc(label))
            rows += Markup(
                '<div class="card"><div class="row"><div class="h4">%s</div>'
                '<span class="pill info">وزن %s</span></div>'
                '<select name="r_%s">%s</select>'
                '<input name="n_%s" placeholder="ملاحظة (اختياري)" value="%s"/></div>'
            ) % (esc(l.name), l.weight, l.id, opts, l.id, esc(l.note or ''))
        sc = 'ok' if a.score >= 75 else ('warn' if a.score >= 60 else 'crit')
        head = Markup(
            '<div class="card"><div class="row"><div class="h4">%s</div>'
            '<span class="pill %s">%.0f%%</span></div>'
            '<div class="muted">%s · %s</div></div>'
        ) % (esc(a.location_id.name or a.facility_id.name or ''), sc, a.score,
             esc(a.name or ''), esc(str(a.audit_date or '')[:16]))
        form = Markup('<form method="post" action="/cafm/m/clean/audit/%s/save">%s%s'
                      '<button class="btn">حفظ النتائج</button></form>') % (a.id, _csrf(), rows)
        close = Markup('')
        if a.state == 'draft':
            close = Markup(
                '<form method="post" action="/cafm/m/clean/audit/%s/close" style="margin-top:8px">%s'
                '<button class="btn g">إنهاء التدقيق وإصدار ملاحظات المخالفات</button></form>'
            ) % (a.id, _csrf())
        return _shell('تدقيق %s' % (a.name or ''), head + form + close, CLN,
                      back='/cafm/m/clean/audit')

    @http.route('/cafm/m/clean/audit/<int:aid>/save', type='http', auth='user',
                methods=['POST'], website=False, csrf=True)
    def audit_save(self, aid, **post):
        a = request.env['care.cafm.clean.audit'].sudo().browse(aid).exists()
        if a:
            for l in a.line_ids:
                r = post.get('r_%s' % l.id)
                if r in ('pass', 'fail', 'na'):
                    l.result = r
                l.note = post.get('n_%s' % l.id) or False
        return request.redirect('/cafm/m/clean/audit/%s' % aid)

    @http.route('/cafm/m/clean/audit/<int:aid>/close', type='http', auth='user',
                methods=['POST'], website=False, csrf=True)
    def audit_close(self, aid, **post):
        """Close the audit and raise a correction note for each failed item —
        the loop the page's own blurb promised but never performed here."""
        env = request.env
        a = env['care.cafm.clean.audit'].sudo().browse(aid).exists()
        if not a:
            return request.redirect('/cafm/m/clean/audit')
        a.state = 'done'
        Obs = env['care.cafm.observation'].sudo() if 'care.cafm.observation' in env else None
        if Obs is not None:
            for l in a.line_ids.filtered(lambda x: x.result == 'fail'):
                vals = {'facility_id': a.facility_id.id}
                if 'location_id' in Obs._fields and a.location_id:
                    vals['location_id'] = a.location_id.id
                if 'title' in Obs._fields:
                    vals['title'] = 'مخالفة تدقيق: %s' % l.name
                if 'description' in Obs._fields:
                    vals['description'] = l.note or 'بند مخالف في تدقيق %s' % (a.name or '')
                try:
                    Obs.create(vals)
                except Exception:
                    pass
        return request.redirect('/cafm/m/clean/audit/%s' % aid)
