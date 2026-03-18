# -*- coding: utf-8 -*-

from odoo import models, fields, api

class EximicionesCosmeticosCorreo(models.Model):
    _name = 'arsante.eximiciones_cosmeticos.correo'
    _description = 'Correos Electrónicos de Eximición Cosmética'

    name = fields.Char(string='Correo Electrónico', required=True)
    eximicion_cosmetico_id = fields.Many2one(
        comodel_name='arsante.eximiciones_cosmeticos',
        string='Eximición Cosmética',
        required=True,
        ondelete='cascade'
    )
