from odoo import http, _
from odoo.addons.portal.controllers.portal import pager as portal_pager, CustomerPortal

ITEMS_PER_PAGE = 3


class ServiceOrderPortal(CustomerPortal):

  def _prepare_home_portal_values(self, counters):
    """ Add subscription details to main account page """
    values = super()._prepare_home_portal_values(counters)
    service_orders_counter = http.request.env['service.order'].search_count([])
    values['service_orders_count'] = service_orders_counter
    return values

  @http.route(
      ['/service_orders', '/service_orders/page/<int:page>'],
      type='http',
      auth="user",
      website=True,
  )
  def portal_service_orders(
      self,
      page=1,
      date_begin=None,
      date_end=None,
      sortby=None,
      filterby=None,
      search=None,
      search_in='content',
      **kw,
  ):
    service_orders_counter = http.request.env['service.order'].search_count([])
    pager = portal_pager(
        url="/service_orders",
        url_args={
            'date_begin': date_begin,
            'date_end': date_end,
            'sortby': sortby,
            'filterby': filterby
        },
        total=service_orders_counter,
        page=page,
        step=ITEMS_PER_PAGE,
    )
    service_orders = http.request.env['service.order'].search(
        [],
        limit=ITEMS_PER_PAGE,
        offset=pager['offset'],
    )
    sortby = 'name'
    return http.request.render(
        'service_order.portal_service_orders',
        {
            "service_orders": service_orders,
            "pager": pager,
            "page_name": 'service_orders',
            "default_url": '/service_orders',
            'sortby': sortby,
        },
    )

  # create order
  @http.route(
      ['/service_order/create'],
      type='http',
      auth="user",
      website=True,
  )
  def portal_service_order_create(self, **kw):
    return http.request.render(
        'service_order.portal_service_order_create',
        {
            "projects": http.request.env['service.project'].search([]).name_get(),
            "types": http.request.env['service.type'].search([]).name_get(),
            "pickup_locations": http.request.env['service.pickup.location'].search([]).name_get(),
        },
    )

  # submit order
  @http.route(
      ['/service_order/submit'],
      type='http',
      auth="user",
      website=True,
      methods=['POST'],
      csrf=False,
  )
  def portal_service_order_submit(self, **kw):
    http.request.env['service.order'].sudo().create(kw)
    return http.request.redirect('/service_orders')
