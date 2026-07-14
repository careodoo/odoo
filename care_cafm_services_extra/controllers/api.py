# -*- coding: utf-8 -*-
# Lightweight JSON API so a STANDALONE (headless) client portal — hosted
# separately, outside Odoo — can consume CAFM data over HTTP.
from odoo import http
from odoo.http import request


class CafmApi(http.Controller):

    def _facilities(self):
        env = request.env
        p = env.user.partner_id
        facs = env['care.cafm.facility'].search(
            ['|', ('partner_id', '=', p.id), ('partner_id', 'child_of', p.commercial_partner_id.id)])
        return facs or env['care.cafm.facility'].search([], limit=5)

    @http.route('/cafm/api/my/services', type='json', auth='user')
    def my_services(self, **kw):
        facs = self._facilities()
        teams = request.env['care.cafm.team'].search([('facility_id', 'in', facs.ids)])
        out, seen = [], set()
        for t in teams:
            if t.service_id.id in seen:
                continue
            seen.add(t.service_id.id)
            out.append({'id': t.service_id.id, 'name': t.service_id.name,
                        'icon': t.service_id.icon, 'members': t.member_count})
        return {'facilities': facs.mapped('name'), 'services': out}

    @http.route('/cafm/api/catalog', type='json', auth='user')
    def catalog(self, **kw):
        Item = request.env.get('care.cafm.catalog.item')
        if Item is None:
            return {'items': []}
        return {'items': [{'id': i.id, 'name': i.name, 'icon': i.icon,
                           'uom': i.uom_name, 'price': i.price} for i in Item.search([])]}

    @http.route('/cafm/api/my/workorders', type='json', auth='user')
    def my_workorders(self, **kw):
        facs = self._facilities()
        wos = request.env['care.cafm.workorder'].search(
            [('facility_id', 'in', facs.ids),
             ('state', 'not in', ('done', 'verified', 'cancelled'))], limit=50)
        return {'count': len(wos), 'workorders': [{
            'name': w.name, 'title': w.title, 'location': w.location_id.name,
            'service': w.service_id.name, 'state': w.state, 'overdue': w.is_overdue,
        } for w in wos]}

    @http.route('/cafm/api/my/requests', type='json', auth='user')
    def my_requests(self, **kw):
        facs = self._facilities()
        Req = request.env.get('care.cafm.request')
        if Req is None:
            return {'requests': []}
        reqs = Req.search([('facility_id', 'in', facs.ids)], limit=50)
        return {'requests': [{'name': r.name, 'state': r.state, 'total': r.amount_total,
                              'lines': r.line_count, 'date': str(r.date)} for r in reqs]}

    @http.route('/cafm/api/request/create', type='json', auth='user')
    def create_request(self, items=None, **kw):
        """items = [{'item_id': id, 'qty': n}, ...] — create a client purchase request."""
        env = request.env
        if 'care.cafm.request' not in env:
            return {'error': 'procurement module not installed'}
        fac = self._facilities()[:1]
        if not fac:
            return {'error': 'no facility'}
        req = env['care.cafm.request'].create({'facility_id': fac.id})
        for it in (items or []):
            cat = env['care.cafm.catalog.item'].browse(int(it.get('item_id')))
            if cat.exists():
                env['care.cafm.request.line'].create({
                    'request_id': req.id, 'item_id': cat.id, 'name': cat.name,
                    'product_id': cat.product_id.id, 'uom_name': cat.uom_name,
                    'price': cat.price, 'qty': float(it.get('qty', 1))})
        return {'id': req.id, 'name': req.name, 'total': req.amount_total}
