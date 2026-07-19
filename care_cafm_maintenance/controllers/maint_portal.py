# -*- coding: utf-8 -*-
"""Maintenance on the web portal — the same console the app carries: report a
fault, work the queue by severity, log the parts consumed, and see what the
periodic inspections are due."""
from markupsafe import Markup

from odoo import fields, http, _
from odoo.http import request

from odoo.addons.care_cafm.controllers.main import _shell, esc

ACCENT = '#f7a23b'

_SEV_COLOR = {'3': '#f2603f', '2': '#f5b638', '1': '#4aa8ff', '0': '#37c98a'}
_STATE_COLOR = {'new': '#4aa8ff', 'assigned': '#f5b638', 'in_progress': '#f59e0b',
                'fixed': '#37c98a', 'closed': '#64748b', 'cancelled': '#94a3b8'}


class MaintPortal(http.Controller):

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
        return Fac.browse(list(ids))

    @http.route('/cafm/m/maint', type='http', auth='user', website=False)
    def board(self, state='open', **kw):
        env = request.env
        facs = self._facilities()
        F = env['care.cafm.maint.fault'].sudo()
        base = [('facility_id', 'in', facs.ids)]
        dom = list(base)
        if state == 'open':
            dom.append(('state', 'not in', ('closed', 'cancelled')))
        elif state != 'all':
            dom.append(('state', '=', state))
        faults = F.search(dom, order='severity desc, reported_date desc', limit=100)

        openf = F.search(base + [('state', 'not in', ('closed', 'cancelled'))])
        crit = len(openf.filtered(lambda f: f.severity == '3'))
        parts = env['care.cafm.maint.part'].sudo().search([])
        low = len(parts.filtered('low_stock'))
        insp_due = env['care.cafm.maint.inspection'].sudo().search_count(
            [('facility_id', 'in', facs.ids), ('state', 'in', ('planned', 'due'))]) \
            if 'state' in env['care.cafm.maint.inspection']._fields else 0

        body = Markup(
            '<div class="kpi">'
            '<div><div class="n">%s</div><div class="l">أعطال مفتوحة</div></div>'
            '<div><div class="n" style="color:%s">%s</div><div class="l">حرِجة</div></div>'
            '<div><div class="n">%s</div><div class="l">فحوص مستحقة</div></div>'
            '<div><div class="n" style="color:%s">%s</div><div class="l">قطع تحت الحد</div></div>'
            '</div>'
        ) % (len(openf), '#f2603f' if crit else '#e9f1fb', crit, insp_due,
             '#f5b638' if low else '#e9f1fb', low)

        body += self._report_form(facs)
        body += self._filters(state)
        if not faults:
            body += Markup('<div class="card"><div class="muted">لا أعطال في هذه الحالة.</div></div>')
        for f in faults:
            body += self._fault_card(f)
        body += self._parts_panel(parts)
        return _shell('الصيانة', body, accent=ACCENT)

    def _csrf(self):
        return Markup('<input type="hidden" name="csrf_token" value="%s"/>') % request.csrf_token()

    def _filters(self, cur):
        opts = [('open', 'المفتوحة'), ('new', 'جديدة'), ('in_progress', 'قيد الإصلاح'),
                ('fixed', 'تم الإصلاح'), ('closed', 'مغلقة'), ('all', 'الكل')]
        out = Markup('<div style="display:flex;gap:7px;flex-wrap:wrap;margin:16px 0 11px">')
        for key, label in opts:
            sel = ('background:%s;color:#0b1220' % ACCENT) if key == cur else 'background:#152438;color:#9cb2cd'
            out += Markup('<a href="/cafm/m/maint?state=%s" class="pill" style="%s;padding:7px 12px">%s</a>') % (
                key, Markup(sel), esc(label))
        return out + Markup('</div>')

    def _report_form(self, facs):
        if not facs:
            return Markup('')
        env = request.env
        fopts = Markup('').join(
            Markup('<option value="%s">%s</option>') % (f.id, esc(f.name)) for f in facs)
        depts = env['care.cafm.maint.department'].sudo().search([])
        dopts = Markup('<option value="">— تلقائي —</option>') + Markup('').join(
            Markup('<option value="%s">%s</option>') % (d.id, esc(d.name)) for d in depts)
        return Markup(
            '<details class="card" style="margin-top:11px">'
            '<summary style="font-weight:900;cursor:pointer">🔧 الإبلاغ عن عطل</summary>'
            '<form method="post" action="/cafm/m/maint/report" style="margin-top:10px">%s'
            '<label>العطل *</label><input name="title" required placeholder="مثال: مصعد متوقف"/>'
            '<label>المرفق</label><select name="facility_id">%s</select>'
            '<label>القسم</label><select name="department_id">%s</select>'
            '<label>الخطورة</label><select name="severity">'
            '<option value="1">منخفضة</option><option value="2" selected>متوسطة</option>'
            '<option value="3">حرِجة — تعطّل خدمة</option></select>'
            '<label>الوصف</label><textarea name="description" rows="3"></textarea>'
            '<button class="btn">إرسال البلاغ</button></form></details>'
        ) % (self._csrf(), fopts, dopts)

    def _fault_card(self, f):
        sev = _SEV_COLOR.get(f.severity, '#4aa8ff')
        st = _STATE_COLOR.get(f.state, '#64748b')
        sev_label = dict(f._fields['severity'].selection).get(f.severity, '')
        st_label = dict(f._fields['state'].selection).get(f.state, f.state)
        meta = ' · '.join(filter(None, [
            f.facility_id.name or '', f.location_id.name or '',
            f.department_id.name or '', f.assignee_id.name or 'غير مُسنَد']))
        extra = Markup('')
        if f.downtime_hours:
            extra += Markup('<span class="pill crit">⏱ تعطّل %s ساعة</span> ') % round(f.downtime_hours, 1)
        if f.parts_cost:
            extra += Markup('<span class="pill info">قطع %s د.ك</span> ') % round(f.parts_cost, 3)
        act = Markup('')
        if f.state in ('new', 'assigned'):
            act = Markup('<form method="post" action="/cafm/m/maint/%s/start">%s'
                         '<button class="btn">▶ بدء الإصلاح</button></form>') % (f.id, self._csrf())
        elif f.state == 'in_progress':
            act = Markup(
                '<form method="post" action="/cafm/m/maint/%s/fix">%s'
                '<label>الإجراء التصحيحي</label><textarea name="resolution" rows="2"></textarea>'
                '<button class="btn" style="background:#37c98a;color:#04201c">✔ تم الإصلاح</button></form>'
            ) % (f.id, self._csrf())
        return Markup(
            '<div class="card stripe" style="border-inline-start-color:%s">'
            '<div class="row"><div class="h4">%s</div>'
            '<span class="pill" style="background:%s22;color:%s">%s</span></div>'
            '<div class="muted">%s</div>'
            '<div style="margin-top:6px"><span class="pill" style="background:%s22;color:%s">%s</span> %s</div>'
            '%s%s</div>'
        ) % (sev, esc(f.title), Markup(st), Markup(st), esc(st_label), esc(meta),
             Markup(sev), Markup(sev), esc(sev_label), extra,
             Markup('<div class="muted" style="margin-top:6px">%s</div>') % esc(f.description) if f.description else Markup(''),
             act)

    def _parts_panel(self, parts):
        low = parts.filtered('low_stock')[:15]
        if not low:
            return Markup('')
        rows = Markup('').join(Markup(
            '<div class="row" style="padding:7px 0;border-top:1px solid #294059">'
            '<div><div class="h4">%s</div><div class="muted">%s</div></div>'
            '<span class="pill warn">%s / %s %s</span></div>'
        ) % (esc(p.name), esc(p.location or p.supplier or '—'),
             round(p.on_hand, 1), round(p.min_qty, 1), esc(p.uom_name or '')) for p in low)
        return Markup(
            '<h3 style="margin:18px 0 9px">قطع غيار تحت الحد الأدنى</h3>'
            '<div class="card">%s</div>'
        ) % rows

    # ---------------- actions ----------------
    @http.route('/cafm/m/maint/report', type='http', auth='user', methods=['POST'],
                website=False, csrf=True)
    def report(self, **post):
        env = request.env
        facs = self._facilities()
        title = (post.get('title') or '').strip()
        fid = int(post.get('facility_id') or 0) or (facs[:1].id if facs else 0)
        if not title or fid not in facs.ids:
            return request.redirect('/cafm/m/maint')
        env['care.cafm.maint.fault'].sudo().create({
            'title': title, 'facility_id': fid,
            'department_id': int(post.get('department_id') or 0) or False,
            'severity': post.get('severity') or '2',
            'description': post.get('description') or False,
            'reported_by': env.user.id, 'reporter_name': env.user.name,
        })
        return request.redirect('/cafm/m/maint')

    @http.route('/cafm/m/maint/<int:fid>/<string:act>', type='http', auth='user',
                methods=['POST'], website=False, csrf=True)
    def action(self, fid, act, **post):
        env = request.env
        f = env['care.cafm.maint.fault'].sudo().browse(fid).exists()
        if not f or f.facility_id.id not in self._facilities().ids:
            return request.redirect('/cafm/m/maint')
        try:
            if act == 'start':
                f.state = 'in_progress'
                if not f.down_since:
                    f.down_since = fields.Datetime.now()
            elif act == 'fix':
                if post.get('resolution'):
                    f.resolution = post['resolution']
                f.state = 'fixed'
                f.restored_at = fields.Datetime.now()
        except Exception:
            pass
        return request.redirect('/cafm/m/maint')
