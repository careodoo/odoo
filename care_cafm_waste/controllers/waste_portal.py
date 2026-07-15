# -*- coding: utf-8 -*-
"""Client portal for the CAFM waste service: list (with stats dashboard),
detail, create, and a period print report — mirroring the legacy service_order
portal but on the new independent models, scoped to the client (incl. CAFM
client sub-users)."""
import base64
import re

from odoo import http, fields, SUPERUSER_ID
from odoo.http import request, content_disposition
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

ITEMS = 20
_PLACEHOLDER = ('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk'
                'YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')


class WasteImg(http.Controller):
    @http.route('/api/v1/cafmwaste/item/<int:iid>/image', type='http', auth='public', csrf=False, cors='*')
    def item_image(self, iid, **kw):
        rec = request.env['cafm.waste.item'].sudo().browse(iid).exists()
        data = rec.image if rec and rec.image else None
        raw = base64.b64decode(data or _PLACEHOLDER)
        return request.make_response(raw, headers=[('Content-Type', 'image/png'),
                                                    ('Content-Length', str(len(raw))),
                                                    ('Cache-Control', 'public, max-age=3600')])


class WastePortal(CustomerPortal):

    def _scope_partner_ids(self):
        user = request.env.user
        p = user.partner_id
        ids = {p.id}
        if p.commercial_partner_id:
            ids.add(p.commercial_partner_id.id)
            ids.update(request.env['res.partner'].sudo().search(
                [('commercial_partner_id', '=', p.commercial_partner_id.id)]).ids)
        if 'care.cafm.client' in request.env:
            clients = request.env['care.cafm.client'].sudo().search([('user_ids', 'in', [user.id])])
            for cp in clients.mapped('partner_id'):
                ids.add(cp.id)
                ids.update(request.env['res.partner'].sudo().search(
                    [('commercial_partner_id', '=', cp.id)]).ids)
        return list(ids)

    def _order_domain(self):
        user = request.env.user
        if user.has_group('base.group_erp_manager') or user.has_group('base.group_system'):
            return []
        projs = request.env['cafm.waste.project'].sudo().search([('contact_id', 'in', self._scope_partner_ids())])
        return [('project_id', 'in', projs.ids)]

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'waste_count' in counters:
            values['waste_count'] = request.env['cafm.waste.order'].sudo().search_count(self._order_domain())
        return values

    @http.route(['/waste/orders', '/waste/orders/page/<int:page>'], type='http', auth='user', website=True)
    def waste_orders(self, page=1, filterby='all', **kw):
        SO = request.env['cafm.waste.order'].sudo()
        base = self._order_domain()
        filters = {
            'all': [], 'open': [('states', 'in', ('draft', 'scheduled', 'pickuped', 'arrived', 'processing'))],
            'completed': [('states', 'in', ('completed', 'delivered'))], 'cancelled': [('states', '=', 'cancelled')],
        }
        domain = base + filters.get(filterby, [])
        total = SO.search_count(domain)
        pager = portal_pager(url='/waste/orders', url_args={'filterby': filterby}, total=total, page=page, step=ITEMS)
        orders = SO.search(domain, limit=ITEMS, offset=pager['offset'], order='serial desc, id desc')
        stats = SO.dashboard_stats(base)
        return request.render('care_cafm_waste.portal_waste_orders', {
            'orders': orders, 'pager': pager, 'page_name': 'waste', 'default_url': '/waste/orders',
            'filterby': filterby, 'waste_stats': stats,
            'searchbar_filters': {k: {'label': k} for k in filters},
        })

    @http.route(['/waste/order/<int:order_id>'], type='http', auth='user', website=True)
    def waste_order_detail(self, order_id, **kw):
        o = request.env['cafm.waste.order'].sudo().browse(order_id).exists()
        if not o or o.id not in request.env['cafm.waste.order'].sudo().search(self._order_domain()).ids:
            return request.redirect('/waste/orders')
        return request.render('care_cafm_waste.portal_waste_order_detail', {'o': o, 'page_name': 'waste'})

    @http.route(['/waste/order/create'], type='http', auth='user', website=True)
    def waste_order_create(self, **kw):
        projs = request.env['cafm.waste.project'].sudo().search(
            [('contact_id', 'in', self._scope_partner_ids())])
        vals = {
            'projects': [(p.id, p.name) for p in projs],
            'types': [(t.id, t.name) for t in request.env['cafm.waste.type'].sudo().search([])],
            'pickups': [(pl.id, pl.name) for pl in request.env['cafm.waste.pickup.location'].sudo().search(
                [('project_id', 'in', projs.ids)])],
            'items': [(i.id, i.name) for i in request.env['cafm.waste.item'].sudo().search([])],
        }
        return request.render('care_cafm_waste.portal_waste_create', vals)

    @http.route(['/waste/order/submit'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def waste_order_submit(self, **post):
        projs = request.env['cafm.waste.project'].sudo().search([('contact_id', 'in', self._scope_partner_ids())])
        pid = int(post.get('project_id')) if post.get('project_id') else (projs[:1].id if projs else False)
        if not pid or pid not in projs.ids:
            return request.redirect('/waste/orders')
        vals = {'project_id': pid, 'request_datetime': post.get('request_datetime') or fields.Datetime.now()}
        if post.get('type_id'):
            vals['type_id'] = int(post['type_id'])
        if post.get('pickup_location_id'):
            vals['pickup_location_id'] = int(post['pickup_location_id'])
        if post.get('notes'):
            vals['notes'] = post['notes']
        lines = []
        if post.get('item_id'):
            lines.append((0, 0, {'item_id': int(post['item_id']), 'quantity': float(post.get('quantity') or 1)}))
        if lines:
            vals['order_line_ids'] = lines
        o = request.env['cafm.waste.order'].sudo().create(vals)
        return request.redirect('/waste/order/%s' % o.id)

    @http.route(['/waste/print'], type='http', auth='user', website=True)
    def waste_print(self, date_from=None, date_to=None, **kw):
        ds = fields.Datetime.from_string(date_from)
        de = fields.Datetime.from_string(date_to).replace(hour=23, minute=59, second=59)
        orders = request.env['cafm.waste.order'].sudo().search(
            self._order_domain() + [('request_datetime', '>=', ds), ('request_datetime', '<=', de)])
        report = request.env.ref('care_cafm_waste.action_report_waste_order').with_user(SUPERUSER_ID)
        pdf = request.env['ir.actions.report'].sudo()._render_qweb_pdf(report, res_ids=orders.ids)[0]
        fname = re.sub(r'\W+', '-', 'waste-report-%s-%s' % (ds.date(), de.date())) + '.pdf'
        return request.make_response(pdf, headers=[('Content-Type', 'application/pdf'),
                                                    ('Content-Disposition', content_disposition(fname))])
