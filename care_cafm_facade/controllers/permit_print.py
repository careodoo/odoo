# -*- coding: utf-8 -*-
"""The height-work permit, printed.

A permit that lives only on a screen is not a permit. The crew on the rope
needs a signed sheet at the anchor point, the safety officer needs it in the
file, and an inspector will ask for it on paper. So it prints as a document
that can carry a signature — with the refusal printed just as plainly as the
approval, because a permit that says NO and looks like a receipt gets ignored.
"""
from markupsafe import Markup, escape

from odoo import http, _
from odoo.http import request

RED = '#c0392b'
INK = '#14202b'


class FacadePermitPrint(http.Controller):

    def _row(self, k, v):
        return Markup('<tr><td class="k">%s</td><td class="v">%s</td></tr>') % (k, v)

    @http.route('/facade/permit/<int:pid>/print', type='http', auth='public',
                website=False, csrf=False, cors='*')
    def permit_print(self, pid, token=None, **kw):
        env = request.env
        tok = token or request.httprequest.args.get('token')
        if tok:
            user = env['care.cafm.mobile.token'].sudo().resolve(tok)
            if user:
                request.update_env(user=user.id)
        elif request.env.user._is_public():
            return request.make_response(_('Not authorised'), status=401)
        p = env['care.cafm.facade.permit'].sudo().browse(pid).exists()
        if not p:
            return request.not_found()

        safe = bool(p.is_safe)
        checks = [
            (_('Risk assessment attached'), p.risk_assessed),
            (_('Equipment and ropes inspected'), p.equipment_checked),
            (_('Wind within the safe limit'),
             bool(p.wind_limit and p.wind_speed <= p.wind_limit)),
        ]
        rows = Markup('').join(
            self._row(k, v) for k, v in [
                (_('Permit number'), p.name or '—'),
                (_('Facility'), p.facility_id.name or '—'),
                (_('Facade / zone'), p.zone_id.name or '—'),
                # `selection` on a related field is a callable here, not a
                # list — asking the field for its description is the only form
                # that works for both.
                (_('Access method'), dict(
                    p._fields['method']._description_selection(env)).get(
                        p.method, p.method or '—')),
                (_('Date'), str(p.date or '')),
                (_('Valid for'), '%s %s' % (p.valid_hours or 0, _('hours'))),
                (_('Wind speed'), '%s / %s %s' % (
                    p.wind_speed or 0, p.wind_limit or 0, _('km/h'))),
                (_('Safety supervisor'), p.supervisor_id.name or '—'),
            ])
        checklist = Markup('').join(
            Markup('<li class="%s">%s %s</li>') % (
                'ok' if v else 'no', '✔' if v else '✘', k) for k, v in checks)
        co = env.company
        logo = (Markup('<img class="logo" src="data:image/png;base64,%s"/>')
                % (co.logo.decode() if isinstance(co.logo, bytes) else co.logo)) if co.logo else Markup('')

        html = ("""<!doctype html><html dir="rtl" lang="ar"><head><meta charset="utf-8"/>
<title>__NAME__</title><style>
*{box-sizing:border-box}
body{font-family:'Tajawal','Segoe UI',Arial,sans-serif;color:__INK__;margin:0;padding:26px;font-size:13px}
.band{padding:14px 18px;border-radius:12px;color:#fff;margin-bottom:18px;
      background:linear-gradient(135deg,__BAND__,__BAND2__)}
.band h1{margin:0;font-size:21px;letter-spacing:.5px}
.band .s{font-size:12.5px;opacity:.92;margin-top:3px}
.hd{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px}
.logo{max-height:44px}
table{width:100%;border-collapse:collapse;margin-bottom:16px}
td{padding:7px 10px;border-bottom:1px solid #e8ecf1}
.k{width:36%;color:#6b7785;font-weight:600}
.v{font-weight:700}
ul{list-style:none;padding:0;margin:0 0 18px}
li{padding:7px 10px;border:1px solid #e8ecf1;border-radius:9px;margin-bottom:6px;font-weight:700}
li.ok{background:#f0fdf4;border-color:#bbf7d0;color:#166534}
li.no{background:#fef2f2;border-color:#fecaca;color:#991b1b}
.sig{display:flex;gap:16px;margin-top:26px}
.sig div{flex:1;border-top:1.5px solid __INK__;padding-top:7px;font-size:11.5px;color:#6b7785}
.warn{padding:12px;border:2px dashed #991b1b;border-radius:10px;color:#991b1b;
      font-weight:800;text-align:center;margin-bottom:16px}
.ft{margin-top:26px;padding-top:9px;border-top:1px solid #e8ecf1;color:#8b97a6;font-size:10.5px;
    display:flex;justify-content:space-between}
@media print{body{padding:10px}}
</style></head><body>
<div class="hd">__LOGO__<div style="text-align:end"><b>__CO__</b></div></div>
<div class="band"><h1>__TITLE__</h1><div class="s">__SUB__</div></div>
__WARN__
<table>__ROWS__</table>
<h3 style="margin:0 0 8px;font-size:14px">__CHECKTITLE__</h3>
<ul>__CHECKS__</ul>
<div class="sig"><div>__SIG1__</div><div>__SIG2__</div><div>__SIG3__</div></div>
<div class="ft"><span>__PRINTED__</span><span>__BY__</span></div>
</body></html>""")
        page = (html
                .replace('__NAME__', str(escape(p.name or '')))
                .replace('__INK__', INK)
                .replace('__BAND__', '#16a34a' if safe else '#991b1b')
                .replace('__BAND2__', '#14532d' if safe else '#450a0a')
                .replace('__LOGO__', str(logo))
                .replace('__CO__', str(escape(co.name or '')))
                .replace('__TITLE__', str(escape(
                    _('HEIGHT WORK PERMIT — APPROVED') if safe
                    else _('HEIGHT WORK PERMIT — NOT APPROVED'))))
                .replace('__SUB__', str(escape(
                    _('This permit authorises the work described below for the stated period only.')
                    if safe else
                    _('Conditions are not met. Work at height must not begin.'))))
                .replace('__WARN__', '' if safe else str(Markup(
                    '<div class="warn">%s</div>') % _(
                    'DO NOT PROCEED — one or more safety conditions failed.')))
                .replace('__ROWS__', str(rows))
                .replace('__CHECKTITLE__', str(escape(_('Safety checks'))))
                .replace('__CHECKS__', str(checklist))
                .replace('__SIG1__', str(escape(_('Safety supervisor'))))
                .replace('__SIG2__', str(escape(_('Crew leader'))))
                .replace('__SIG3__', str(escape(_('Client representative'))))
                .replace('__PRINTED__', '%s %s' % (
                    _('Printed'), str(request.env.cr.now() if hasattr(request.env.cr, 'now') else '')[:16]))
                .replace('__BY__', str(escape(env.user.name or ''))))
        return request.make_response(page, headers=[
            ('Content-Type', 'text/html; charset=utf-8')])

    @http.route('/facade/permit/<int:pid>/pdf', type='http', auth='public',
                website=False, csrf=False, cors='*')
    def permit_pdf(self, pid, token=None, **kw):
        html = self.permit_print(pid, token=token).data
        if isinstance(html, bytes):
            html = html.decode('utf-8')
        pdf = request.env['ir.actions.report'].sudo()._run_wkhtmltopdf(
            [html], landscape=False,
            specific_paperformat_args={
                'data-report-margin-top': 8, 'data-report-margin-bottom': 8,
                'data-report-margin-left': 8, 'data-report-margin-right': 8})
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename="permit-%s.pdf"' % pid)])
