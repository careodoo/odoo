# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

import base64
from odoo import http, tools, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class PortalAccount(CustomerPortal):

    @http.route('/my/resignation', type='http', auth="user", website=True)
    def resignation_details(self, access_token=None, **kw):

        resignation_sudo = request.env['hr.employee.resignation'].sudo().search(
            [('state', '!=', 'done'), ('create_uid', '=', request.env.uid)], limit=1, order="id desc")
        #     return request.redirect("%s?error=%s" % ('/my/resignation', 'Not Allowed.'))
        if resignation_sudo:
            resignation_id = resignation_sudo
            kw['resignation_id'] = resignation_id
        return request.render("nthub_hr_resignation.portal_resignation", kw)

    @http.route('/create/resignation/request', type='http', auth='user', website=True, csrf=False)
    def resignation_request_form(self, create_from_header=None, **kw):
        # employee_id = request.env['hr.employee'].get_employee()
        employee_ids = request.env['hr.employee'].sudo().search([])
        # if employee_id:
        #     kw['employee_id'] = employee_id
        if create_from_header:
            kw['create_from_header'] = True
        kw['page_name'] = 'resignation_create'
        kw['ticket_date'] = fields.Date.today()
        kw['resignation_id'] = False
        kw['employee_ids'] = employee_ids
        return request.render("nthub_hr_resignation.portal_resignation", kw)

    @http.route('/resignation/request', type='http', auth='public', website=True)
    def apply4resignation(self, **post):
        if post.get('resignation_id'):
            resignation_id = request.env['hr.employee.resignation'].sudo().browse(int(post.get('resignation_id')))
        else:
            resignation_id = False
        attached_files = request.httprequest.files.getlist('ufile')
        try:
            if len(post) > 1:
                values = post
                for value in ['resignation_id', 'ufile']:
                    post.pop(value)
                values['employee_id'] = int(values['employee_id'])
                if resignation_id:
                    resignation_id.check_access_rights('write')
                    resignation_id.write(values)
                    self.btrip_attchcreate(attached_files, resignation_id)
                    # if resignation_id.state == 'draft':
                    #     resignation_id.action_confirm()
                    return request.render("nthub_hr_resignation.thankyou_resignation", {'record': resignation_id})
                else:
                    record = request.env['hr.employee.resignation'].sudo().create(values)
                    if record:
                        self.btrip_attchcreate(attached_files, record)
                    return request.render("nthub_hr_resignation.thankyou_resignation", {'record': record})
        except Exception as e:
            request.env.cr.rollback()
            return request.redirect("/my/trips?error=%s" % tools.ustr(e))

    def btrip_attchcreate(self, ufiles, record):
        for file in ufiles:
            ufile = file.read()
            vals = {
                'res_model': 'hr.employee.resignation',
                'res_id': record.id,
                'datas': base64.b64encode(ufile),
                'type': 'binary',
                'name': file.filename,
            }
            request.env['ir.attachment'].sudo().create(vals)
