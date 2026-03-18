# -*- coding: utf-8 -*-

from odoo import models, fields, api

class RegistroCosmeticoCorreo(models.Model):
    _name = 'arsante.registro_cosmetico.correo'
    _description = 'Correos Electrónicos de Registro Cosmético'

    name = fields.Char(string='Correo Electrónico', required=True)
    registro_cosmetico_id = fields.Many2one(
        comodel_name='arsante.registro_cosmetico',
        string='Registro Cosmético',
        required=True,
        ondelete='cascade'
    )
