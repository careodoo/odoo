# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import http, _
from odoo.http import request
from odoo.addons.care_cafm.controllers.main import _shell, ACCENTS, esc

FAC = ACCENTS['facade']


class CafmFacadeMobile(http.Controller):

    @http.route('/cafm/m/facade', type='http', auth='user', website=False)
    def facade_home(self, **kw):
        env = request.env
        permits = env['care.cafm.facade.permit'].search(
            [('state', 'in', ('submitted', 'approved', 'active'))], limit=8)
        zones_due = env['care.cafm.facade.zone'].search([('is_due', '=', True)], limit=8)
        prows = Markup('')
        for p in permits:
            wind = Markup('<span class="pill crit">⛔ رياح %skm/h</span>') % int(p.wind_speed) if not p.is_safe \
                else Markup('<span class="pill ok">رياح آمنة</span>')
            if p.state == 'submitted':
                act = Markup('<a class="pill ok" href="/cafm/m/facade/%s/approve">اعتماد</a>') % p.id
            elif p.state == 'approved':
                act = Markup('<a class="pill ok" href="/cafm/m/facade/%s/start">▶ بدء</a>') % p.id
            else:
                act = Markup('<a class="pill info" href="/cafm/m/facade/%s/close">إنهاء</a>') % p.id
            prows += Markup('<div class="card"><div class="h4">%s · %s</div>'
                            '<div class="muted">%s · %s</div><div style="margin-top:6px">%s</div></div>'
                            ) % (esc(p.name), esc(p.zone_id.name or ''), esc(p.facility_id.name or ''), wind, act)
        if not permits:
            prows = Markup('<div class="card muted">لا تصاريح نشطة.</div>')
        zrows = Markup('')
        for z in zones_due:
            zrows += Markup('<div class="card row"><div><div class="h4">%s</div>'
                            '<div class="muted">%s · مستحقّة</div></div><span class="pill warn">تنظيف</span></div>'
                            ) % (esc(z.name), esc(dict(z._fields['method'].selection).get(z.method)))
        if not zones_due:
            zrows = Markup('<div class="card muted">لا واجهات مستحقّة.</div>')
        body = Markup(
            '<div class="card"><div class="h4">⚠️ العمل على الارتفاع يتطلّب تصريحاً + رياح آمنة</div></div>'
            '<h3 style="margin:12px 0 10px">التصاريح النشطة</h3>%s'
            '<h3 style="margin:16px 0 10px">واجهات مستحقّة التنظيف</h3>%s'
        ) % (prows, zrows)
        return _shell('الواجهات', body, FAC)

    @http.route('/cafm/m/facade/<int:pid>/<string:act>', type='http', auth='user', website=False)
    def facade_act(self, pid, act, **kw):
        p = request.env['care.cafm.facade.permit'].browse(pid)
        if p.exists():
            try:
                if act == 'approve':
                    p.action_approve()
                elif act == 'start':
                    p.action_start()
                elif act == 'close':
                    p.action_close()
            except Exception as e:
                body = Markup('<div class="card"><div class="big" style="color:#f2603f">⛔</div>'
                              '<p class="muted">%s</p></div><a class="btn" href="/cafm/m/facade">عودة</a>'
                              ) % esc(str(e))
                return _shell('تنبيه', body, FAC, back='/cafm/m/facade')
        return request.redirect('/cafm/m/facade')
