# -*- coding: utf-8 -*-
from odoo import http

# class Arsante(http.Controller):
#     @http.route('/arsante/arsante/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/arsante/arsante/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('arsante.listing', {
#             'root': '/arsante/arsante',
#             'objects': http.request.env['arsante.arsante'].search([]),
#         })

#     @http.route('/arsante/arsante/objects/<model("arsante.arsante"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('arsante.object', {
#             'object': obj
#         })