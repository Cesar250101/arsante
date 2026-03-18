# -*- coding: utf-8 -*-

from odoo import models, fields

class ModificacionCosmeticosCorreo(models.Model):
    _name = 'arsante.modificacion_cosmeticos.correo'
    _description = 'Correos Electrónicos de Modificación Cosmética'

    name = fields.Char(string='Correo Electrónico', required=True)
    modificacion_cosmetico_id = fields.Many2one(
        comodel_name='arsante.modificacion_cosmeticos',
        string='Modificación Cosmética',
        required=True,
        ondelete='cascade'
    )
