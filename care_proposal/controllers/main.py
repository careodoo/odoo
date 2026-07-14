import base64

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class ServiceRequestController(http.Controller):

    @http.route(['/service-request'], type='http', auth='public', website=True, sitemap=True)
    def sr_form(self, **kw):
        types = request.env['proposal.service.type'].sudo().search([])
        return request.render('care_proposal.service_request_form', {
            'service_types': types,
            'values': kw,
        })

    @http.route(['/service-request/submit'], type='http', auth='public',
                website=True, methods=['POST'], csrf=True)
    def sr_submit(self, **post):
        user = request.env.user
        partner = False if user._is_public() else user.partner_id
        vals = {
            'source': 'portal',
            'partner_id': partner.id if partner else False,
            'contact_name': post.get('contact_name') or (partner and partner.name),
            'contact_email': post.get('contact_email') or (partner and partner.email),
            'contact_phone': post.get('contact_phone'),
            'company_name': post.get('company_name'),
            'service_type_id': int(post['service_type_id']) if post.get('service_type_id') else False,
            'site_location': post.get('site_location'),
            'city': post.get('city'),
            'description': post.get('description'),
            'duration': post.get('duration'),
            'budget_range': post.get('budget_range'),
        }
        if post.get('desired_start_date'):
            vals['desired_start_date'] = post['desired_start_date']
        sr = request.env['proposal.service.request'].sudo().create(vals)
        # attachments (optional)
        att_ids = []
        for f in request.httprequest.files.getlist('attachments'):
            if f and f.filename:
                att = request.env['ir.attachment'].sudo().create({
                    'name': f.filename,
                    'datas': base64.b64encode(f.read()),
                    'res_model': 'proposal.service.request',
                    'res_id': sr.id,
                })
                att_ids.append(att.id)
        if att_ids:
            sr.sudo().attachment_ids = [(6, 0, att_ids)]
        return request.render('care_proposal.service_request_thanks', {'sr': sr})

    @http.route(['/service-request/track'], type='http', auth='public',
                website=True, methods=['GET', 'POST'], csrf=True)
    def sr_track(self, **post):
        sr, error = False, False
        if request.httprequest.method == 'POST':
            number = (post.get('number') or '').strip()
            email = (post.get('email') or '').strip().lower()
            found = request.env['proposal.service.request'].sudo().search(
                [('name', '=', number)], limit=1)
            if found and (found._recipient_email() or '').lower() == email:
                sr = found
            else:
                error = "Request not found, or the email does not match our records."
        return request.render('care_proposal.service_request_track',
                              {'sr': sr, 'error': error, 'values': post})


class ServiceRequestPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'sr_count' in counters:
            partner = request.env.user.partner_id
            values['sr_count'] = request.env['proposal.service.request'].search_count(
                ['|', ('partner_id', '=', partner.id),
                 ('partner_id', '=', partner.commercial_partner_id.id)])
        return values

    def _sr_domain(self):
        partner = request.env.user.partner_id
        return ['|', ('partner_id', '=', partner.id),
                ('partner_id', '=', partner.commercial_partner_id.id)]

    @http.route(['/my/service-requests', '/my/service-requests/page/<int:page>'],
                type='http', auth='user', website=True)
    def my_service_requests(self, page=1, **kw):
        SR = request.env['proposal.service.request']
        domain = self._sr_domain()
        total = SR.search_count(domain)
        pager = portal_pager(url='/my/service-requests', total=total, page=page, step=20)
        reqs = SR.search(domain, limit=20, offset=pager['offset'], order='create_date desc')
        return request.render('care_proposal.portal_my_service_requests', {
            'requests': reqs, 'pager': pager, 'page_name': 'service_request',
            'default_url': '/my/service-requests',
        })

    @http.route(['/my/service-request/<int:request_id>'],
                type='http', auth='user', website=True)
    def my_service_request(self, request_id, **kw):
        sr = request.env['proposal.service.request'].browse(request_id)
        try:
            sr.check_access_rights('read')
            sr.check_access_rule('read')
        except Exception:
            return request.redirect('/my')
        return request.render('care_proposal.portal_service_request_detail',
                              {'sr': sr, 'page_name': 'service_request'})
