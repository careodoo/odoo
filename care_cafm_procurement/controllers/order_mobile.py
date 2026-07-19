# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import http, _
from odoo.http import request
from odoo.addons.care_cafm.controllers.main import _shell, ACCENTS, esc, _csrf

TEAL = ACCENTS['disinfection']


class CafmOrderMobile(http.Controller):

    def _draft(self):
        env = request.env
        partner = env.user.partner_id
        fac = env['care.cafm.facility'].search(
            ['|', ('partner_id', '=', partner.id), ('partner_id', 'child_of', partner.commercial_partner_id.id)], limit=1)
        if not fac:
            # Falling back to "any facility" put a user with no site of their own
            # into another tenant's basket. Better to have no cart at all.
            return env['care.cafm.request']
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
            cart += Markup(
                '<div class="card"><div class="row"><div><div class="h4">%s</div>'
                '<div class="muted">%.3f د.ك</div></div>'
                '<form method="post" action="/cafm/m/order/line/%s/remove" style="margin:0">%s'
                '<button class="pill crit" style="border:none;cursor:pointer;font-family:inherit">حذف</button>'
                '</form></div>'
                '<form method="post" action="/cafm/m/order/line/%s/qty" '
                'style="display:flex;gap:8px;align-items:end;margin-top:8px">%s'
                '<div style="flex:1"><label>الكمية</label>'
                '<input name="qty" type="number" min="1" step="1" value="%s"/></div>'
                '<button class="btn g" style="width:auto;margin:0;padding:11px 14px">تحديث</button>'
                '</form></div>'
            ) % (esc(l.name), l.subtotal, l.id, _csrf(), l.id, _csrf(), int(l.qty))
        catalog = Markup('')
        for it in items:
            catalog += Markup('<div class="card row"><div><div class="h4">%s %s</div>'
                              '<div class="muted">%s · %.3f د.ك</div></div>'
                              '<form method="post" action="/cafm/m/order/add" style="margin:0">%s'
                              '<input type="hidden" name="item" value="%s"/>'
                              '<button class="pill ok" style="border:none;cursor:pointer;font-family:inherit">'
                              '＋ أضف</button></form></div>'
                              ) % (esc(it.icon or '📦'), esc(it.name), esc(it.uom_name or ''),
                                   it.price, _csrf(), it.id)
        if not items:
            catalog = Markup('<div class="card muted">لا كتالوج معرّف.</div>')
        submit = (Markup('<form method="post" action="/cafm/m/order/submit">%s'
                         '<button class="btn">إرسال الطلب للاعتماد (%.3f د.ك)</button></form>')
                  % (_csrf(), req.amount_total)) if req.line_ids else Markup('')
        body = Markup(
            '<div class="card"><div class="h4">🛒 طلبك — %s</div>'
            '<div class="muted">%s صنف · الإجمالي %.3f د.ك</div></div>%s%s'
            '<h3 style="margin:16px 0 10px">الكتالوج المعتمد</h3>%s'
        ) % (esc(req.name or ''), req.line_count, req.amount_total,
             (Markup('<h4 class="h4" style="margin:6px 0">سلّتك</h4>') + cart) if req.line_ids else Markup(''),
             submit, catalog)
        return _shell('مشترياتي', body, TEAL)

    @http.route('/cafm/m/order/add', type='http', auth='user',
                methods=['POST'], website=False, csrf=True)
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

    @http.route('/cafm/m/order/submit', type='http', auth='user',
                methods=['POST'], website=False, csrf=True)
    def order_submit(self, **kw):
        req = self._draft()
        if req and req.line_ids:
            req.action_submit()
            body = Markup('<div class="card"><div class="big" style="color:#37c98a">✔ أُرسل الطلب</div>'
                          '<p class="muted">%s — بانتظار الاعتماد ثم التوريد.</p></div>'
                          '<a class="btn" href="/cafm/m/order">طلب جديد</a>') % esc(req.name)
            return _shell('تم', body, TEAL)
        return request.redirect('/cafm/m/order')

    def _own_line(self, lid):
        """A cart line the caller's own draft owns — never someone else's."""
        req = self._draft()
        if not req:
            return None
        line = request.env['care.cafm.request.line'].sudo().browse(lid).exists()
        return line if (line and line.request_id == req and req.state == 'draft') else None

    @http.route('/cafm/m/order/line/<int:lid>/remove', type='http', auth='user',
                methods=['POST'], website=False, csrf=True)
    def line_remove(self, lid, **post):
        line = self._own_line(lid)
        if line:
            line.unlink()
        return request.redirect('/cafm/m/order')

    @http.route('/cafm/m/order/line/<int:lid>/qty', type='http', auth='user',
                methods=['POST'], website=False, csrf=True)
    def line_qty(self, lid, **post):
        line = self._own_line(lid)
        try:
            qty = int(post.get('qty') or 0)
        except ValueError:
            qty = 0
        if line and qty > 0:
            line.qty = qty
        elif line:
            line.unlink()
        return request.redirect('/cafm/m/order')
