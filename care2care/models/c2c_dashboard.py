# -*- coding: utf-8 -*-
"""Data provider for the CARE 2 CARE app control-center dashboard."""
from datetime import timedelta
from odoo import api, fields, models


class C2CBookingDashboard(models.Model):
    _inherit = 'c2c.booking'

    @api.model
    def get_app_dashboard(self):
        env = self.env
        B = env['c2c.booking'].sudo()
        today = fields.Date.context_today(self)
        now = fields.Datetime.now()
        bookings = B.search([])
        by_state = {}
        for s, _l in B._fields['state'].selection:
            by_state[s] = len(bookings.filtered(lambda b: b.state == s))
        paid_book = sum(bookings.filtered(lambda b: b.payment_state == 'paid').mapped('amount'))

        Order = env['c2c.product.order'].sudo() if 'c2c.product.order' in env else None
        orders = Order.search([]) if Order is not None else Order
        order_rev = sum(o.amount_total for o in orders) if orders else 0.0

        Contract = env['c2c.contract.request'].sudo() if 'c2c.contract.request' in env else None
        contracts = Contract.search([]) if Contract is not None else Contract

        # customers = distinct partners across bookings + orders
        cust = set(bookings.mapped('partner_id').ids)
        if orders:
            cust |= set(orders.mapped('partner_id').ids)

        # top services by bookings
        svc_count = {}
        for b in bookings:
            if b.service_id:
                svc_count[b.service_id] = svc_count.get(b.service_id, 0) + 1
        top_services = sorted(svc_count.items(), key=lambda kv: -kv[1])[:6]

        # 14-day booking series
        series = []
        for i in range(13, -1, -1):
            d = today - timedelta(days=i)
            cnt = len(bookings.filtered(lambda b: b.visit_datetime and b.visit_datetime.date() == d))
            series.append({'label': d.strftime('%m-%d'), 'value': cnt})

        def rec_list(recs, kind):
            out = []
            for r in recs:
                if kind == 'booking':
                    out.append({'id': r.id, 'name': r.name, 'title': r.service_id.name or '',
                                'sub': (r.partner_id.name or ''), 'state': r.state,
                                'amount': r.amount, 'model': 'c2c.booking'})
                elif kind == 'order':
                    out.append({'id': r.id, 'name': r.name, 'title': '%d منتج' % r.item_count,
                                'sub': (r.partner_id.name or ''), 'state': r.state,
                                'amount': r.amount_total, 'model': 'c2c.product.order'})
                else:
                    out.append({'id': r.id, 'name': r.name, 'title': r.title,
                                'sub': (r.customer_name or ''), 'state': r.state,
                                'amount': r.quote_amount or 0, 'model': 'c2c.contract.request'})
            return out

        return {
            'kpis': {
                'services': env['c2c.service'].sudo().search_count([]),
                'categories': env['c2c.category'].sudo().search_count([]),
                'offers': env['c2c.offer'].sudo().search_count([('is_live', '=', True)]) if 'c2c.offer' in env else 0,
                'subscriptions': env['c2c.subscription.plan'].sudo().search_count([]) if 'c2c.subscription.plan' in env else 0,
                'providers': env['c2c.provider'].sudo().search_count([]) if 'c2c.provider' in env else 0,
                'customers': len(cust),
                'bookings': len(bookings),
                'bookings_today': len(bookings.filtered(lambda b: b.visit_datetime and b.visit_datetime.date() == today)),
                'bookings_active': by_state.get('confirmed', 0) + by_state.get('assigned', 0) + by_state.get('in_progress', 0),
                'orders': len(orders),
                'orders_open': len([o for o in orders if o.state in ('draft', 'confirmed', 'shipped')]) if orders else 0,
                'contracts': len(contracts),
                'contracts_new': len([c for c in contracts if c.state in ('new', 'reviewing', 'quoted')]) if contracts else 0,
                'revenue': round(paid_book + order_rev, 2),
                'currency': env.company.currency_id.name,
            },
            'booking_states': [{'state': k, 'label': dict(B._fields['state'].selection).get(k), 'count': v} for k, v in by_state.items()],
            'top_services': [{'name': s.name, 'count': c} for s, c in top_services],
            'series': series,
            'recent_bookings': rec_list(bookings.sorted('id', reverse=True)[:6], 'booking'),
            'recent_orders': rec_list((orders.sorted('id', reverse=True)[:5]) if orders else [], 'order'),
            'recent_contracts': rec_list((contracts.sorted('id', reverse=True)[:5]) if contracts else [], 'contract'),
        }
