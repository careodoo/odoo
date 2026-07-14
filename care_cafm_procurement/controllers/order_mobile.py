# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import http, _
from odoo.http import request
from odoo.addons.care_cafm.controllers.main import _shell, ACCENTS, esc

TEAL = ACCENTS['disinfection']


class CafmOrderMobile(http.Controller):

    def _draft(self):
        env = request.env
        partner = env.user.partner_id
        fac = env['care.cafm.facility'].search(
            ['|', ('partner_id', '=', partner.id), ('partner_id', 'child_of', partner.commercial_partner_id.id)], limit=1)
        if not fac:
            fac = env['care.cafm.facility'].search([], limit=1)
        req = env['care.cafm.request'].search(
            [('facility_id', '=', fac.id), ('state', '=', 'draft')], limit=1)
        if not req and fac:
            req = env['care.cafm.request'].create({'facility_id': fac.id})
        return req

    @http.route('/cafm/m/order', type='http', auth='user', website=False)
    def order(self, **kw):
        env = request.env
        req = self._draft()
        items = env['care.cafm.catalog.item'].search([], limit=30)
        cart = Markup('')
        for l in req.line_ids:
            cart += Markup('<div class="card row"><div><div class="h4">%s ×%s</div>'
                           '<div class="muted">%.3f د.ك</div></div></div>'
                           ) % (esc(l.name), int(l.qty), l.subtotal)
        catalog = Markup('')
        for it in items:
            catalog += Markup('<div class="card row"><div><div class="h4">%s %s</div>'
                              '<div class="muted">%s · %.3f د.ك</div></div>'
                              '<a class="pill ok" href="/cafm/m/order/add?item=%s">＋ أضف</a></div>'
                              ) % (esc(it.icon or '📦'), esc(it.name), esc(it.uom_name or ''), it.price, it.id)
        if not items:
            catalog = Markup('<div class="card muted">لا كتالوج معرّف.</div>')
        submit = Markup('<a class="btn" href="/cafm/m/order/submit">إرسال الطلب للاعتماد (%.3f د.ك)</a>') % req.amount_total if req.line_ids else Markup('')
        body = Markup(
            '<div class="card"><div class="h4">🛒 طلبك — %s</div>'
            '<div class="muted">%s صنف · الإجمالي %.3f د.ك</div></div>%s%s'
            '<h3 style="margin:16px 0 10px">الكتالوج المعتمد</h3>%s'
        ) % (esc(req.name or ''), req.line_count, req.amount_total,
             (Markup('<h4 class="h4" style="margin:6px 0">سلّتك</h4>') + cart) if req.line_ids else Markup(''),
             submit, catalog)
        return _shell('مشترياتي', body, TEAL)

    @http.route('/cafm/m/order/add', type='http', auth='user', website=False)
    def order_add(self, item=None, **kw):
        env = request.env
        req = self._draft()
        it = env['care.cafm.catalog.item'].browse(int(item)) if item else False
        if req and it:
            line = req.line_ids.filtered(lambda l: l.item_id == it)[:1]
            if line:
                line.qty += 1
            else:
                env['care.cafm.request.line'].create({
                    'request_id': req.id, 'item_id': it.id, 'name': it.name,
                    'product_id': it.product_id.id, 'uom_name': it.uom_name, 'price': it.price, 'qty': 1})
        return request.redirect('/cafm/m/order')

    @http.route('/cafm/m/order/submit', type='http', auth='user', website=False)
    def order_submit(self, **kw):
        req = self._draft()
        if req and req.line_ids:
            req.action_submit()
            body = Markup('<div class="card"><div class="big" style="color:#37c98a">✔ أُرسل الطلب</div>'
                          '<p class="muted">%s — بانتظار الاعتماد ثم التوريد.</p></div>'
                          '<a class="btn" href="/cafm/m/order">طلب جديد</a>') % esc(req.name)
            return _shell('تم', body, TEAL)
        return request.redirect('/cafm/m/order')
