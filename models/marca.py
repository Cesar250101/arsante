# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _

class Marcas(models.Model):
    _name = 'arsante.marcas'

    name = fields.Char(string='Nombre Registro')
    url_onedrive = fields.Char(string='URL OneDrive')
    

