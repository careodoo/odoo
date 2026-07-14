# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import http, _
from odoo.http import request
from odoo.addons.care_cafm.controllers.main import _shell, ACCENTS, esc

AGR = ACCENTS['agriculture']


class CafmAgriMobile(http.Controller):

    @http.route('/cafm/m/agri', type='http', auth='user', website=False)
    def agri_home(self, **kw):
        env = request.env
        zones = env['care.cafm.agri.zone'].search([], limit=12)
        plants = env['care.cafm.agri.plant'].search_count([])
        due = zones.filtered('is_due')
        zrows = Markup('')
        for z in zones:
            tag = Markup('<span class="pill warn">مستحق</span>') if z.is_due else Markup('<span class="pill ok">مروي</span>')
            smart = Markup(' <span class="pill info">ذكي</span>') if z.weather_based else Markup('')
            zrows += Markup('<div class="card row"><div><div class="h4">%s%s</div>'
                            '<div class="muted">%s · %s</div></div>'
                            '<a class="pill ok" href="/cafm/m/agri/run/%s">💧 ريّ</a> %s</div>'
                            ) % (esc(z.name), smart, esc(dict(z._fields['method'].selection).get(z.method)),
                                 esc(dict(z._fields['frequency'].selection).get(z.frequency)), z.id, tag)
        if not zones:
            zrows = Markup('<div class="card muted">لا مناطق ريّ معرّفة.</div>')
        body = Markup(
            '<div class="kpi"><div><div class="n">%s</div><div class="l">مناطق مستحقّة</div></div>'
            '<div><div class="n">%s</div><div class="l">نباتات مسجّلة</div></div></div>'
            '<h3 style="margin:14px 0 10px">مناطق الريّ</h3>%s'
        ) % (len(due), plants, zrows)
        return _shell('الزراعة', body, AGR)

    @http.route('/cafm/m/agri/run/<int:zid>', type='http', auth='user', website=False)
    def agri_run(self, zid, **kw):
        z = request.env['care.cafm.agri.zone'].browse(zid)
        if z.exists():
            z.action_run()
        return request.redirect('/cafm/m/agri')
