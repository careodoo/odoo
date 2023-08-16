# -*- coding: utf-8 -*-
from odoo import http

# class BonusRequest(http.Controller):
#     @http.route('/bonus_request/bonus_request/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/bonus_request/bonus_request/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('bonus_request.listing', {
#             'root': '/bonus_request/bonus_request',
#             'objects': http.request.env['bonus_request.bonus_request'].search([]),
#         })

#     @http.route('/bonus_request/bonus_request/objects/<model("bonus_request.bonus_request"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('bonus_request.object', {
#             'object': obj
#         })