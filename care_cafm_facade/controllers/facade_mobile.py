# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import http, _
from odoo.http import request
from odoo.addons.care_cafm.controllers.main import _shell, ACCENTS, esc

FAC = ACCENTS['facade']


def _act_form(pid, act, label, cls):
    """A permit action is a POST with a CSRF token — never a link."""
    return Markup(
        '<form method="post" action="/cafm/m/facade/%s/%s" style="display:inline;margin:0">'
        '<input type="hidden" name="csrf_token" value="%s"/>'
        '<button class="pill %s" style="border:none;cursor:pointer;font-family:inherit">%s</button>'
        '</form>') % (pid, act, request.csrf_token(), Markup(cls), esc(label))


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
            # A permit gates work at height. Approving one must be a deliberate
            # POST by someone entitled to, not a link any crawler can follow.
            if p.state == 'submitted':
                act = _act_form(p.id, 'approve', 'اعتماد', 'ok')
            elif p.state == 'approved':
                act = _act_form(p.id, 'start', '▶ بدء', 'ok')
            else:
                act = _act_form(p.id, 'close', 'إنهاء', 'info')
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

    def _may_act(self, permit):
        """Only staff, or a client user whose facility this is and who holds the
        work-order permission, may move a height permit. This route used to
        accept any logged-in user on a GET."""
        env = request.env
        u = env.user
        if u.has_group('base.group_system') or u.has_group('base.group_erp_manager'):
            return True
        if u.employee_id:
            return True
        par = u.partner_id.commercial_partner_id or u.partner_id
        client = env['care.cafm.client'].sudo().search(
            [('partner_id', '=', par.id)], limit=1) if par else None
        if not client or not client.can('workorder_verify'):
            return False
        facs = env['care.cafm.facility'].sudo().search([('partner_id', '=', par.id)])
        return permit.facility_id.id in facs.ids

    @http.route('/cafm/m/facade/<int:pid>/<string:act>', type='http', auth='user',
                methods=['POST'], website=False, csrf=True)
    def facade_act(self, pid, act, **kw):
        p = request.env['care.cafm.facade.permit'].browse(pid)
        if p.exists() and not self._may_act(p):
            return request.redirect('/cafm/m/facade')
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
