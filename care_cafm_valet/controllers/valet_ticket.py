# -*- coding: utf-8 -*-
"""The printed valet ticket, and the page a guest reaches by scanning it.

A guest has no account and no app — they have a slip of paper. So the QR on that
slip carries a token, the page it opens is public, and the only thing it can do
is ask for that one car. Asking pushes the request to whoever is on shift.
"""
import base64
import io as _io

from markupsafe import Markup, escape

from odoo import http, _
from odoo.http import request

RED = '#b45309'
INK = '#14202b'


def _qr_data_uri(text):
    """A QR as an inline data URI — the ticket must print from any browser
    without fetching anything."""
    try:
        import qrcode
        img = qrcode.make(text, box_size=8, border=2)
        buf = _io.BytesIO()
        img.save(buf, format='PNG')
        return 'data:image/png;base64,%s' % base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


def _base_url():
    return request.env['ir.config_parameter'].sudo().get_param(
        'web.base.url', 'https://ecare.care-kw.com').rstrip('/')



def _caller():
    """The app carries a bearer token, not a session cookie. These routes were
    auth='user', so every print from the app was redirected to the login page
    and arrived as HTML — which is the "error" when printing a ticket. Accept
    the token, fall back to a real web session for the back office."""
    req = request.httprequest
    tok = (req.args.get('token')
           or (req.headers.get('Authorization', '').replace('Bearer ', '').strip() or None))
    if tok:
        try:
            user = request.env['care.cafm.mobile.token'].sudo().resolve(tok)
            if user:
                return user
        except Exception:
            pass
    u = request.env.user
    return u if u and not u._is_public() else None


class ValetTicketPortal(http.Controller):

    # ---------------- the printable ticket (staff) ----------------
    @http.route('/valet/ticket/<int:tid>/print', type='http', auth='public',
                website=False, csrf=False, cors='*')
    def ticket_print(self, tid, **kw):
        if not _caller():
            return request.make_response(_('Not authorized'), status=401)
        t = request.env['care.valet.ticket'].sudo().browse(tid).exists()
        if not t:
            return request.not_found()
        url = '%s/valet/t/%s' % (_base_url(), t.qr_token or '')
        qr = _qr_data_uri(url)
        rows = [
            (_('Ticket Number'), t.name),
            (_('Plate'), t.plate),
            # A claim slip, not a file: only what is needed to return the car.
            (_('Vehicle'), ' '.join(filter(None, [t.car_make, t.car_color])) or '—'),
            (_('Key'), t.key_tag or '—'),
            (_('Spot'), t.spot_id.name or t.zone_id.name or '—'),
            # The date matters as much as the time: a ticket found in a
            # drawer is useless if you cannot tell which day it belongs to.
            (_('Date & time'), str(t.received_at or '')[:16]),
        ]
        body = Markup('').join(
            Markup('<tr><td class="k">%s</td><td class="v">%s</td></tr>') % (k, v or '—')
            for k, v in rows)
        note = Markup('<div class="note"><b>Vehicle condition notes:</b> %s</div>') % t.damage_note \
            if t.damage_note else Markup('')
        qr_block = (Markup('<img src="%s" alt="QR"/>') % qr) if qr else Markup(
            '<div class="noqr">%s</div>') % url

        # A plain str template: Markup.replace() ESCAPES what it is given, so
        # substituting the rows into a Markup template turned every <tr> into
        # visible text on the printed ticket. The fragments below are already
        # safe Markup; the free-text values are escaped explicitly.
        html = ("""<!doctype html><html lang="ar" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__NAME__</title><style>
*{box-sizing:border-box}
body{margin:0;background:#eef1f5;font-family:"Segoe UI",Tahoma,system-ui,"Noto Sans Arabic",sans-serif;
     display:flex;justify-content:center;padding:8px}
.t{width:260px;background:#fff;border-radius:16px;overflow:hidden;
   box-shadow:0 10px 30px -12px rgba(0,0,0,.35)}
.h{background:linear-gradient(150deg,__RED__,#7a3906);color:#fff;padding:9px 12px;text-align:center}
.h .b{font-size:9px;letter-spacing:2px;opacity:.85}
.h img{max-height:26px;margin-bottom:4px;filter:brightness(0) invert(1)}
.h .n{font-size:17px;font-weight:900;margin-top:2px;letter-spacing:1px}
.h .p{font-size:13px;font-weight:800;margin-top:4px;background:rgba(255,255,255,.16);
      display:inline-block;padding:3px 10px;border-radius:7px}
table{width:100%;border-collapse:collapse;font-size:10.5px}
td{padding:4px 11px;border-bottom:1px solid #f1f4f7}
.k{color:#7d8b9c;width:42%}
.v{font-weight:800;color:__INK__}
.qr{text-align:center;padding:9px}
.qr img{width:112px;height:112px}
.qr .c{font-size:9.5px;color:#7d8b9c;margin-top:5px;line-height:1.45}
.qr .c b{color:__INK__}
.note{margin:0 11px 9px;padding:7px;background:#fff6ed;border:1px solid #f3d9bd;
      border-radius:8px;font-size:9.5px;color:#7a3906}
.f{background:#f7f8fa;padding:6px;text-align:center;font-size:8.5px;color:#8b97a6}
.pr{display:block;margin:14px auto 0;background:__RED__;color:#fff;border:none;
    border-radius:11px;padding:12px 26px;font-size:15px;font-weight:900;cursor:pointer;
    font-family:inherit}
@media print{body{background:#fff;padding:0}.t{box-shadow:none;width:auto}.pr{display:none}}
</style></head><body>
<div>
<div class="t">
  <div class="h">__LOGO__<div class="b">CARE VALET</div><div class="n">__NAME__</div>
    <div class="p">__PLATE__</div></div>
  <table>__ROWS__</table>
  __NOTE__
  <div class="qr">__QR__
    <div class="c"><b>To request your car:</b> Scan the code with your phone camera<br/>and the request reaches the valet team instantly</div>
  </div>
  <div class="f">Keep this ticket — the vehicle is released to its holder</div>
</div>
<button class="pr" onclick="window.print()">🖨️ Print Ticket</button>
</div></body></html>""")
        # The header carried an empty band where a logo belonged. Print the
        # company logo when there is one, and close the gap when there is not.
        logo = ''
        co = t.company_id or request.env.company
        if co and co.logo:
            logo = ('<img src="data:image/png;base64,%s"/>'
                    % (co.logo.decode() if isinstance(co.logo, bytes) else co.logo))
        page = (html.replace('__LOGO__', logo)
                .replace('__NAME__', escape(t.name or ''))
                .replace('__PLATE__', escape(t.plate or ''))
                .replace('__RED__', RED).replace('__INK__', INK)
                .replace('__ROWS__', str(body)).replace('__NOTE__', str(note))
                .replace('__QR__', str(qr_block)))
        return request.make_response(page, headers=[('Content-Type', 'text/html; charset=utf-8')])

    @http.route('/valet/ticket/<int:tid>/pdf', type='http', auth='public',
                website=False, csrf=False, cors='*')
    def ticket_pdf(self, tid, **kw):
        """The same slip as a PDF, so the app can show it inline and offer
        print and share instead of throwing the user into a browser."""
        if not _caller():
            return request.make_response(_('Not authorized'), status=401)
        t = request.env['care.valet.ticket'].sudo().browse(tid).exists()
        if not t:
            return request.not_found()
        html = self.ticket_print(tid).data
        if isinstance(html, bytes):
            html = html.decode('utf-8')
        # drop the on-screen print button — it means nothing on paper
        html = html.replace('<button class="pr" onclick="window.print()">🖨️ Print Ticket</button>', '')
        pdf = request.env['ir.actions.report'].sudo()._run_wkhtmltopdf(
            [html], landscape=False,
            specific_paperformat_args={
                'data-report-margin-top': 6, 'data-report-margin-bottom': 6,
                'data-report-margin-left': 6, 'data-report-margin-right': 6,
            })
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename="%s.pdf"' % (t.name or 'valet').replace('/', '-')),
        ])

    # ---------------- the guest page (public, token only) ----------------
    @http.route('/valet/t/<string:token>', type='http', auth='public', website=False,
                sitemap=False)
    def guest_ticket(self, token, **kw):
        t = request.env['care.valet.ticket'].sudo().search(
            [('qr_token', '=', token)], limit=1)
        if not t:
            return request.make_response(self._page(
                '⚠️', 'Unknown ticket', 'Please make sure you scanned the correct code.', ''),
                headers=[('Content-Type', 'text/html; charset=utf-8')])

        state = t.state
        if state == 'delivered':
            return request.make_response(self._page(
                '✅', 'Vehicle handed over', 'Thank you for using the CARE valet service.', t.plate),
                headers=[('Content-Type', 'text/html; charset=utf-8')])
        if state == 'requested':
            mins = int(t.retrieval_minutes or 0)
            return request.make_response(self._page(
                '⏱️', 'Your request is in progress',
                'Our team is retrieving your vehicle now — %s minutes elapsed.' % mins, t.plate),
                headers=[('Content-Type', 'text/html; charset=utf-8')])

        action = Markup(
            '<form method="post" action="/valet/t/%s/request">'
            '<button class="cta">🚗 Request My Vehicle Now</button></form>'
            '<div class="hint">The request reaches the valet team instantly, and average retrieval time is %s minutes.</div>'
        ) % (token, t.sla_minutes or 7)
        return request.make_response(
            self._page('🚗', 'Your vehicle is ready to request',
                       'Press the button when you are on your way to the exit.', t.plate, extra=action),
            headers=[('Content-Type', 'text/html; charset=utf-8')])

    @http.route('/valet/t/<string:token>/request', type='http', auth='public',
                methods=['POST'], website=False, csrf=False, sitemap=False)
    def guest_request(self, token, **post):
        """CSRF is off deliberately. A guest is anonymous — there is no session
        and no ambient authority for a third party to ride on, and Odoo will not
        mint a usable token for a session it never persisted. The capability here
        is the unguessable token printed on the ticket: holding it *is* being the
        person holding the car's ticket. It can only ever request this one car,
        and only while that car is parked."""
        t = request.env['care.valet.ticket'].sudo().search(
            [('qr_token', '=', token)], limit=1)
        if t and t.state in ('received', 'parked'):
            t.action_request(by_guest=True)
        return request.redirect('/valet/t/%s' % token)

    def _page(self, icon, title, sub, plate, extra=Markup('')):
        # Same trap as the ticket: a Markup template escapes what replace()
        # puts into it, so the CTA button and the plate block arrived as
        # visible source instead of markup.
        html = ("""<!doctype html><html lang="ar" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__ · CARE Valet</title><style>
*{box-sizing:border-box}
body{margin:0;min-height:100vh;background:linear-gradient(160deg,__RED__,#5c2a04);
     color:#fff;font-family:"Segoe UI",Tahoma,system-ui,"Noto Sans Arabic",sans-serif;
     display:flex;align-items:center;justify-content:center;padding:22px}
.c{width:100%;max-width:380px;text-align:center}
.i{font-size:64px}
h1{font-size:23px;font-weight:900;margin:12px 0 6px}
.s{font-size:14px;opacity:.85;line-height:1.7}
.plate{display:inline-block;margin-top:16px;background:rgba(255,255,255,.14);
       border:1px solid rgba(255,255,255,.25);border-radius:12px;
       padding:10px 22px;font-size:21px;font-weight:900;letter-spacing:2px}
.cta{display:block;width:100%;margin-top:26px;background:#fff;color:__RED__;border:none;
     border-radius:14px;padding:17px;font-size:17px;font-weight:900;cursor:pointer;
     font-family:inherit;box-shadow:0 10px 24px -10px rgba(0,0,0,.5)}
.hint{font-size:12px;opacity:.75;margin-top:12px;line-height:1.6}
.b{margin-top:30px;font-size:11px;letter-spacing:3px;opacity:.6}
</style></head><body><div class="c">
<div class="i">__ICON__</div><h1>__TITLE__</h1><div class="s">__SUB__</div>
__PLATE__ __EXTRA__
<div class="b">CARE VALET</div>
</div></body></html>""")
        plate_html = (Markup('<div class="plate">%s</div>') % plate) if plate else Markup('')
        return (html.replace('__ICON__', str(icon))
                .replace('__TITLE__', str(escape(title)))
                .replace('__SUB__', str(escape(sub))).replace('__RED__', RED)
                .replace('__PLATE__', str(plate_html)).replace('__EXTRA__', str(extra)))
