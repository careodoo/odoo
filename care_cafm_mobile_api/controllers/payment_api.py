# -*- coding: utf-8 -*-
"""In-app invoice payment via UPayments.

Flow:
  1. App taps «دفع» → POST /client/invoice/<id>/pay-link → we create a hosted
     UPayments charge for the invoice's outstanding amount and hand back its
     payment URL.
  2. The app opens that URL in an in-app WebView. UPayments hosts the card entry.
  3. On completion UPayments (a) redirects to /upay/return|cancel — which the
     WebView detects to close — and (b) calls /upay/webhook, where we settle the
     invoice by registering a payment against it.

Reconciliation lives in the webhook (server-to-server, trustworthy). The return
page is UX only.
"""
import logging
import secrets

from odoo import fields
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _body, API

_logger = logging.getLogger(__name__)


class PaymentApi(Controller):

    # ---- helpers ----------------------------------------------------------
    def _provider(self, env):
        return env['payment.provider'].sudo().search(
            [('code', '=', 'upayments')], limit=1)

    def _base(self):
        # Prefer the configured public URL; fall back to the request host so
        # webhooks resolve to a reachable address in every deployment.
        base = request.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', '') or request.httprequest.host_url
        return base.rstrip('/')

    def _mark_paid(self, env, inv, amount=0.0):
        """Register a payment against the invoice so it settles. Idempotent —
        a second webhook for an already-paid invoice does nothing."""
        inv = inv.sudo()
        if inv.state != 'posted' or inv.payment_state in ('paid', 'in_payment', 'reversed'):
            return False
        if inv.amount_residual <= 0:
            return False
        journal = env['account.journal'].sudo().search(
            [('type', 'in', ('bank', 'cash')), ('company_id', '=', inv.company_id.id)],
            limit=1)
        if not journal:
            _logger.warning('UPay: no bank/cash journal for company %s', inv.company_id.id)
            return False
        pay_amount = min(amount or inv.amount_residual, inv.amount_residual)
        reg = env['account.payment.register'].sudo().with_context(
            active_model='account.move', active_ids=inv.ids).create({
                'amount': pay_amount,
                'journal_id': journal.id,
                'payment_date': fields.Date.context_today(inv),
                'communication': inv.x_upay_ref or inv.name,
            })
        reg.action_create_payments()
        inv.message_post(body='💳 تم استلام الدفع عبر UPayments: %.3f %s' % (
            pay_amount, inv.currency_id.name or ''))
        return True

    def _done_page(self, ok):
        title = 'تم الدفع بنجاح' if ok else 'أُلغيت عملية الدفع'
        icon = '✅' if ok else '↩️'
        color = '#16a34a' if ok else '#64748b'
        html = """<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>%s</title><style>
body{margin:0;height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;
font-family:system-ui,'Tajawal',sans-serif;background:#f4f6fa;color:#0f1b2d}
.ic{font-size:64px;margin-bottom:12px}.t{font-size:19px;font-weight:800;color:%s}
.s{color:#64748b;margin-top:8px;font-size:13px}</style></head>
<body><div class="ic">%s</div><div class="t">%s</div>
<div class="s">يمكنك العودة إلى التطبيق الآن</div></body></html>""" % (title, color, icon, title)
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])

    # ---- create a payment link -------------------------------------------
    @route(API + '/client/invoice/<int:mid>/pay-link', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def pay_link(self, mid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        inv = env['account.move'].sudo().browse(mid).exists()
        if not inv or inv.move_type not in ('out_invoice', 'out_refund'):
            return _err('فاتورة غير موجودة', 404)
        # Ownership: a client may only pay their own invoices.
        u = env.user
        if not u.has_group('base.group_user'):
            cpid = u.partner_id.commercial_partner_id.id
            if inv.commercial_partner_id.id != cpid:
                return _err('غير مصرّح', 403)
        if inv.state != 'posted':
            return _err('الفاتورة غير معتمدة', 422)
        if inv.amount_residual <= 0:
            return _err('الفاتورة مدفوعة بالكامل', 422)
        prov = self._provider(env)
        if not prov or not prov.upay_application_key:
            return _err('بوابة الدفع غير مهيّأة. يرجى إعداد UPayments.', 503)

        ref = 'INV%s-%s' % (inv.id, secrets.token_hex(6))
        inv.x_upay_ref = ref
        base = self._base()
        p = inv.partner_id
        payload = {
            'order': {
                'id': ref, 'reference': ref,
                'description': inv.name or ('فاتورة %s' % inv.id),
                'currency': inv.currency_id.name or 'KWD',
                'amount': round(inv.amount_residual, 3),
            },
            'language': 'ar',
            'reference': {'id': ref},
            'plugin': {'src': 'odoo'},
            'customer': {
                'uniqueId': str(p.id),
                'name': p.name or 'Customer',
                'email': p.email or '',
                'mobile': p.phone or p.mobile or '',
            },
            'returnUrl': '%s%s/upay/return?ref=%s' % (base, API, ref),
            'cancelUrl': '%s%s/upay/cancel?ref=%s' % (base, API, ref),
            'notificationUrl': '%s%s/upay/webhook' % (base, API),
        }
        try:
            res = prov._upayments_make_request(payload=payload)
        except Exception as e:
            _logger.exception('UPay pay-link failed for invoice %s', inv.id)
            return _err('تعذّر إنشاء رابط الدفع: %s' % e, 502)
        return _ok({
            'payment_url': res.get('form_url'),
            'ref': ref,
            'amount': round(inv.amount_residual, 3),
            'currency': inv.currency_id.name or 'KWD',
            'return_url': payload['returnUrl'],
            'cancel_url': payload['cancelUrl'],
        })

    # ---- gateway callbacks ------------------------------------------------
    @route(API + '/upay/webhook', type='http', auth='public',
           methods=['POST', 'GET'], csrf=False, cors='*')
    def upay_webhook(self, **kw):
        env = request.env
        data = {}
        try:
            data = _body() or {}
        except Exception:
            data = {}
        data = {**kw, **(data if isinstance(data, dict) else {})}
        order = data.get('order') if isinstance(data.get('order'), dict) else {}
        ref = (data.get('reference') or order.get('reference') or order.get('id')
               or data.get('order_id') or data.get('merchantRequestedOrderId'))
        status = str(data.get('result') or data.get('status')
                     or data.get('is_success') or data.get('paymentStatus') or '').lower()
        ok = status in ('captured', 'success', 'successful', 'true', '1', 'paid', 'completed')
        if ref:
            inv = env['account.move'].sudo().search([('x_upay_ref', '=', ref)], limit=1)
            if inv and ok:
                try:
                    amt = float(data.get('amount') or (order.get('amount') if order else 0) or 0)
                except (TypeError, ValueError):
                    amt = 0.0
                try:
                    self._mark_paid(env, inv, amt)
                except Exception:
                    _logger.exception('UPay webhook: settle failed for %s', ref)
        return request.make_response('OK', headers=[('Content-Type', 'text/plain')])

    @route(API + '/upay/return', type='http', auth='public', csrf=False, cors='*')
    def upay_return(self, **kw):
        return self._done_page(True)

    @route(API + '/upay/cancel', type='http', auth='public', csrf=False, cors='*')
    def upay_cancel(self, **kw):
        return self._done_page(False)

    # ---- app polls this after the WebView closes, so settlement shows even
    #      if the webhook is momentarily delayed --------------------------
    @route(API + '/client/invoice/<int:mid>/pay-status', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def pay_status(self, mid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        inv = env['account.move'].sudo().browse(mid).exists()
        if not inv:
            return _err('غير موجودة', 404)
        return _ok({
            'payment_state': inv.payment_state,
            'amount_residual': inv.amount_residual,
            'paid': inv.payment_state in ('paid', 'in_payment'),
        })
