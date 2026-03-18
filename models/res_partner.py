# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    url_documentos = fields.Char(
        string='URL Documentos',
    )
    url_todomoda = fields.Char(
        string='URL Todo Moda',
    )
    url_isadora = fields.Char(
        string='URL Isadora',
    )


    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        if self.env.company.es_arsante:
            self = self.with_context(es_arsante=True)
        return super().get_view(view_id, view_type, **options)
