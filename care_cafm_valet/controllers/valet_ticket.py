# -*- coding: utf-8 -*-
"""The printed valet ticket, and the page a guest reaches by scanning it.

A guest has no account and no app — they have a slip of paper. So the QR on that
slip carries a token, the page it opens is public, and the only thing it can do
is ask for that one car. Asking pushes the request to whoever is on shift.
"""
import base64
import io as _io

from markupsafe import Markup

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
            return request.make_response(_('غير مصرّح'), status=401)
        t = request.env['care.valet.ticket'].sudo().browse(tid).exists()
        if not t:
            return request.not_found()
        url = '%s/valet/t/%s' % (_base_url(), t.qr_token or '')
        qr = _qr_data_uri(url)
        rows = [
            (_('رقم التذكرة'), t.name),
            (_('اللوحة'), t.plate),
            (_('المركبة'), ' '.join(filter(None, [t.car_make, t.car_model, t.car_color])) or '—'),
            (_('رقم المفتاح'), t.key_tag or '—'),
            (_('الضيف'), t.guest_name or '—'),
            (_('الهاتف'), t.guest_phone or '—'),
            (_('المرفق'), t.facility_id.name or '—'),
            (_('الموقف'), t.spot_id.name or t.zone_id.name or '—'),
            (_('وقت الاستلام'), str(t.received_at or '')[:16]),
            (_('استلمها'), t.received_by.sudo().name or '—'),
        ]
        body = Markup('').join(
            Markup('<tr><td class="k">%s</td><td class="v">%s</td></tr>') % (k, v or '—')
            for k, v in rows)
        note = Markup('<div class="note"><b>ملاحظات حالة المركبة:</b> %s</div>') % t.damage_note \
            if t.damage_note else Markup('')
        qr_block = (Markup('<img src="%s" alt="QR"/>') % qr) if qr else Markup(
            '<div class="noqr">%s</div>') % url

        html = Markup("""<!doctype html><html lang="ar" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__NAME__</title><style>
*{box-sizing:border-box}
body{margin:0;background:#eef1f5;font-family:"Segoe UI",Tahoma,system-ui,"Noto Sans Arabic",sans-serif;
     display:flex;justify-content:center;padding:18px}
.t{width:360px;background:#fff;border-radius:16px;overflow:hidden;
   box-shadow:0 10px 30px -12px rgba(0,0,0,.35)}
.h{background:linear-gradient(150deg,__RED__,#7a3906);color:#fff;padding:16px 18px;text-align:center}
.h .b{font-size:12px;letter-spacing:3px;opacity:.85}
.h .n{font-size:24px;font-weight:900;margin-top:2px;letter-spacing:1px}
.h .p{font-size:15px;font-weight:800;margin-top:6px;background:rgba(255,255,255,.16);
      display:inline-block;padding:5px 14px;border-radius:9px}
table{width:100%;border-collapse:collapse;font-size:13px}
td{padding:8px 18px;border-bottom:1px solid #eef1f5}
.k{color:#7d8b9c;width:42%}
.v{font-weight:800;color:__INK__}
.qr{text-align:center;padding:16px}
.qr img{width:180px;height:180px}
.qr .c{font-size:12.5px;color:#7d8b9c;margin-top:8px;line-height:1.6}
.qr .c b{color:__INK__}
.note{margin:0 18px 14px;padding:10px;background:#fff6ed;border:1px solid #f3d9bd;
      border-radius:10px;font-size:12px;color:#7a3906}
.f{background:#f7f8fa;padding:11px;text-align:center;font-size:11px;color:#8b97a6}
.pr{display:block;margin:14px auto 0;background:__RED__;color:#fff;border:none;
    border-radius:11px;padding:12px 26px;font-size:15px;font-weight:900;cursor:pointer;
    font-family:inherit}
@media print{body{background:#fff;padding:0}.t{box-shadow:none;width:auto}.pr{display:none}}
</style></head><body>
<div>
<div class="t">
  <div class="h"><div class="b">CARE VALET</div><div class="n">__NAME__</div>
    <div class="p">__PLATE__</div></div>
  <table>__ROWS__</table>
  __NOTE__
  <div class="qr">__QR__
    <div class="c"><b>لطلب سيارتك:</b> امسح الرمز بكاميرا هاتفك<br/>وسيصل الطلب فورًا لطاقم الفاليه</div>
  </div>
  <div class="f">احتفظ بهذه التذكرة — تُسلَّم المركبة لحاملها</div>
</div>
<button class="pr" onclick="window.print()">🖨️ طباعة التذكرة</button>
</div></body></html>""")
        page = (html.replace('__NAME__', str(t.name or ''))
                .replace('__PLATE__', str(t.plate or ''))
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
            return request.make_response(_('غير مصرّح'), status=401)
        t = request.env['care.valet.ticket'].sudo().browse(tid).exists()
        if not t:
            return request.not_found()
        html = self.ticket_print(tid).data
        if isinstance(html, bytes):
            html = html.decode('utf-8')
        # drop the on-screen print button — it means nothing on paper
        html = html.replace('<button class="pr" onclick="window.print()">🖨️ طباعة التذكرة</button>', '')
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
                '⚠️', 'تذكرة غير معروفة', 'تأكّد من مسح الرمز الصحيح.', ''),
                headers=[('Content-Type', 'text/html; charset=utf-8')])

        state = t.state
        if state == 'delivered':
            return request.make_response(self._page(
                '✅', 'تم تسليم المركبة', 'شكرًا لاستخدامكم خدمة CARE للفاليه.', t.plate),
                headers=[('Content-Type', 'text/html; charset=utf-8')])
        if state == 'requested':
            mins = int(t.retrieval_minutes or 0)
            return request.make_response(self._page(
                '⏱️', 'طلبك قيد التنفيذ',
                'الطاقم يُحضر مركبتك الآن — مضى %s دقيقة.' % mins, t.plate),
                headers=[('Content-Type', 'text/html; charset=utf-8')])

        action = Markup(
            '<form method="post" action="/valet/t/%s/request">'
            '<button class="cta">🚗 اطلب مركبتي الآن</button></form>'
            '<div class="hint">سيصل الطلب فورًا لطاقم الفاليه، ومتوسط زمن الإحضار %s دقائق.</div>'
        ) % (token, t.sla_minutes or 7)
        return request.make_response(
            self._page('🚗', 'مركبتك جاهزة للطلب',
                       'اضغط الزر عندما تكون في طريقك للمخرج.', t.plate, extra=action),
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
        html = Markup("""<!doctype html><html lang="ar" dir="rtl"><head>
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
        return (html.replace('__ICON__', icon).replace('__TITLE__', str(title))
                .replace('__SUB__', str(sub)).replace('__RED__', RED)
                .replace('__PLATE__', str(plate_html)).replace('__EXTRA__', str(extra)))
