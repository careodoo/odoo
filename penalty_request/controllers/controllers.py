# -*- coding: utf-8 -*-
from odoo import http

# class PenaltyRequest(http.Controller):
#     @http.route('/penalty_request/penalty_request/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/penalty_request/penalty_request/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('penalty_request.listing', {
#             'root': '/penalty_request/penalty_request',
#             'objects': http.request.env['penalty_request.penalty_request'].search([]),
#         })

#     @http.route('/penalty_request/penalty_request/objects/<model("penalty_request.penalty_request"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('penalty_request.object', {
#             'object': obj
#         })