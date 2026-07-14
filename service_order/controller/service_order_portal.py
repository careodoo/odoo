from datetime import datetime
from odoo import http, _, SUPERUSER_ID, fields
from odoo.addons.portal.controllers.portal import pager as portal_pager, CustomerPortal
from odoo.exceptions import AccessError, MissingError
from odoo.tools import html2plaintext
from odoo.osv.expression import AND, OR
import pytz
import re
from dateutil.relativedelta import relativedelta

ITEMS_PER_PAGE = 10


class ServiceOrderPortal(CustomerPortal):

  def get_timezone_offset(self):
    tz = http.request.env.user.tz
    offset = 2
    if tz:
      timezone = pytz.timezone(tz)
      aware1 = timezone.localize(datetime.now())
      offset = aware1.utcoffset().seconds / 3600
    return offset

  def convert_input_datetime(self, time):
    offset = self.get_timezone_offset()
    try:
      return datetime.strptime(time, '%Y-%m-%dT%H:%M:%S') - relativedelta(hours=offset)
    except:
      return datetime.strptime(time, '%Y-%m-%dT%H:%M') - relativedelta(hours=offset)

  def _get_order_search_domain(self, search_in, search):
    search_domain = []
    if search_in in ('all', 'serial'):
      search_domain = OR([search_domain, [('serial', 'ilike', search)]])
    if search_in in ('all', 'notes'):
      search_domain = OR([search_domain, [('notes', 'ilike', search)]])
    return search_domain

  def _get_portal_default_domain(self):
    return []

  def _prepare_home_portal_values(self, counters):
    """ Add subscription details to main account page.
    Only count/show for users who actually have access to service.order —
    otherwise the async portal counter endpoint raises AccessError and pops
    an error on every user's «My Account» page. """
    values = super()._prepare_home_portal_values(counters)
    if 'service_orders_count' in counters:
      SO = http.request.env['service.order']
      values['service_orders_count'] = SO.search_count([]) \
          if SO.check_access_rights('read', raise_exception=False) else 0
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
      groupby='none',
      **kw,
  ):
    if not http.request.env['service.order'].check_access_rights('read', raise_exception=False):
      # users without access shouldn't land here (card is hidden for them);
      # if reached directly, send them back to the portal home gracefully.
      return http.request.redirect('/my')
    domain = self._get_portal_default_domain()
    searchbar_filters = {
        'all': {'label': _('All'), 'domain': []},
        'draft': {'label': _('Draft'), 'domain': [('states', '=', 'draft')]},
        'scheduled': {'label': _('Scheduled'), 'domain': [('states', '=', 'scheduled')]},
        'cancelled': {'label': _('Cancelled'), 'domain': [('states', '=', 'cancelled')]},
        'completed': {'label': _('Completed'), 'domain': [('states', '=', 'completed')]},
        'delivered': {'label': _('Delivered'), 'domain': [('states', '=', 'delivered')]},
        'processing': {'label': _('Processing'), 'domain': [('states', '=', 'processing')]},
        'arrived': {'label': _('Arrived'), 'domain': [('states', '=', 'arrived')]},
        'pickuped': {'label': _('Pickuped'), 'domain': [('states', '=', 'pickuped')]},

    }
    searchbar_inputs = {
        'all': {'label': _('Search in All'), 'input': 'all'},
        'serial': {'label': _('Search in serial'), 'input': 'serial'},
        'notes': {'label': _('Search in Notes'), 'input': 'notes'},
    }
    searchbar_sortings = {
        'serial desc': {'label': _('Serial Desc'), 'order': 'serial desc'},
        'name': {'label': _('Serial'), 'order': 'serial'},
        'request_datetime': {'label': _('Order Date'), 'order': 'request_datetime'},
        'id': {'label': _('ID'), 'order': 'id'},
    }

    if not sortby:
      sortby = 'serial desc'
    order = searchbar_sortings[sortby]['order']

    # ========================= filter by =========================
    if not filterby:
      filterby = 'all'
    domain = AND([domain, searchbar_filters[filterby]['domain']])
    # ========================= search =========================
    if search and search_in:
      domain = AND([domain, self._get_order_search_domain(search_in, search)])
    # ========================= group by =========================
    if not groupby:
      groupby = 'none'

    service_orders_counter = http.request.env['service.order'].search_count([])
    pager = portal_pager(
        url="/service_orders",
        url_args={
            'date_begin': date_begin,
            'date_end': date_end,
            'sortby': sortby,
            'filterby': filterby,
            'search_in': search_in,
            'search': search,
            'groupby': groupby,
        },
        total=service_orders_counter,
        page=page,
        step=ITEMS_PER_PAGE,
    )
    service_orders = http.request.env['service.order'].search(
        domain,
        limit=ITEMS_PER_PAGE,
        offset=pager['offset'],
        order=order,
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
            'searchbar_filters': searchbar_filters,
            'searchbar_inputs': searchbar_inputs,
            'searchbar_sortings': searchbar_sortings,
            'filterby': filterby,
            'search_in': search_in,
            'search': search,
            'timzone_offset': self.get_timezone_offset(),
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
            "items": http.request.env['service.item'].search([]).name_get(),
            "page_name": 'order_create',
        },
    )

  # submit order
  @http.route(
      ['/service_order/submit', '/service_order/submit/<int:order_id>'],
      type='http',
      auth="user",
      website=True,
      methods=['POST'],
      csrf=False,
  )
  def portal_service_order_submit(self, order_id=None, **kw):
    if order_id:
      datetime_converted = self.convert_input_datetime(kw.get('order_datetime'))
      order = http.request.env['service.order'].browse(order_id)
      order.sudo().write({
          'project_id': int(kw.get('project_id')),
          'type_id': int(kw.get('type_id')),
          'pickup_location_id': int(kw.get('pickup_location_id')),
          'order_datetime': datetime_converted,
          'notes': kw.get('notes'),
      })
      # notify user
      order.sudo().message_post(
          body=_('Order updated by customer'),
          message_type='comment',)

      return http.request.redirect(f'/service_order/{order_id}')
    else:
      datetime_converted = self.convert_input_datetime(kw.get('request_datetime'))
      order_id = http.request.env['service.order'].sudo().create({
          **kw,
          'request_datetime': datetime_converted,
      })
      # send notification
      http.request.env['mail.activity'].sudo().create({
          'res_id':
              order_id,
          'res_model_id':
              http.request.env['ir.model'].sudo().search([('model', '=', 'service.order')]).id,
          'activity_type_id':
              http.request.env['mail.activity.type'].sudo().search([('name', '=', 'To Do')]).id,
          'summary':
              'New order created',
      })
      return http.request.redirect('/service_orders')

  # view order
  @http.route(
      ['/service_order/<int:order_id>/'],
      type='http',
      auth="user",
      website=True,
  )
  def portal_service_order_details(
      self,
      order_id,
      report_type=None,
      access_token=None,
      download=None,
      **kw,
  ):
    order = http.request.env['service.order'].browse(order_id)
    try:
      order_sudo = self._document_check_access(
          'service.order',
          order_id,
          access_token=access_token,
      )
    except (AccessError, MissingError):
      return http.request.redirect('/service_orders')

    if report_type in ('html', 'pdf', 'text'):
      return self._show_report(
          model=order_sudo.trip_id,
          report_type=report_type,
          report_ref='service_order.action_report_service_trip_pdf',
          download=download,
      )
    return http.request.render(
        'service_order.portal_service_order_details',
        {
            "service_order": order,
            "page_name": 'order_details',
            "timzone_offset": self.get_timezone_offset(),
        },
    )

  # update order
  @http.route(
      ['/service_order/<int:order_id>/update'],
      type='http',
      auth="user",
      website=True,
  )
  def portal_service_order_update(self, order_id, **kw):
    order = http.request.env['service.order'].browse(order_id)
    return http.request.render(
        'service_order.portal_service_order_update',
        {
            "service_order": order,
            "order_notes": html2plaintext(order.notes),
            "projects": http.request.env['service.project'].search([]).name_get(),
            "types": http.request.env['service.type'].search([]).name_get(),
            "pickup_locations": http.request.env['service.pickup.location'].search([]).name_get(),
            'timzone_offset': self.get_timezone_offset(),
        },
    )

  # cancel order
  @http.route(
      ['/service_order/<int:order_id>/cancel'],
      type='http',
      auth="user",
      website=True,
  )
  def portal_service_order_cancel(self, order_id, **kw):
    order = http.request.env['service.order'].browse(order_id)
    if order.trip_id:
      order.sudo().trip_id.action_to_cancelled()
    else:
      order.sudo().action_to_cancelled()
    return http.request.redirect(f'/service_order/{order_id}')

  # print list of orders
  @http.route(
      ['/service_order/print'],
      type='http',
      auth="user",
      website=True,
  )
  def portal_service_order_print(
      self,
      date_from=None,
      date_to=None,
      **kw,
  ):
    date_start = fields.Datetime.from_string(date_from)
    date_end = fields.Datetime.from_string(date_to).replace(hour=23, minute=59, second=59)
    orders = http.request.env['service.order'].search([
        ('order_datetime', '>=', date_start),
        ('order_datetime', '<=', date_end),
    ])
    report_sudo = http.request.env.ref('service_order.action_report_service_order_pdf').with_user(
        SUPERUSER_ID)
    report = http.request.env["ir.actions.report"].sudo()._render_qweb_pdf(
        report_sudo,
        res_ids=orders.ids,
        data={
            'report_type': 'pdf',
            'date_from': date_start.date(),
            'date_to': date_end.date(),
            'timzone_offset': self.get_timezone_offset(),
        },
    )[0]
    reporthttpheaders = [
        ('Content-Type', 'application/pdf'),
        ('Content-Length', len(report)),
    ]
    filename = "%s.pdf" % (re.sub(
        r'\W+',
        '-',
        'Disposable Report from %s to %s' % (date_start.date(), date_end.date()),
    ))
    reporthttpheaders.append(('Content-Disposition', http.content_disposition(filename)))
    return http.request.make_response(report, headers=reporthttpheaders)
