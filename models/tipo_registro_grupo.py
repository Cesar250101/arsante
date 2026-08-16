# -*- coding: utf-8 -*-
"""Agrupador de tipos de registro para el menú lateral.

Hoy ``arsante.tipo_registro._sync_menu()`` cuelga el menú de cada tipo
directo del menú raíz «Tipo de Registros» (más de 20 entradas en una sola
lista plana). Este modelo es la unidad de agrupación (ej. «Cosméticos»,
«Dispositivos Médicos») que un paso posterior usará para anidar esos menús
por grupo en vez de dejarlos todos al mismo nivel.
"""

from odoo import fields, models


class TipoRegistroGrupo(models.Model):
    _name = 'arsante.tipo_registro.grupo'
    _description = 'Grupo de Tipos de Registro'
    _order = 'sequence, name'

    name = fields.Char(string='Nombre', required=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    menu_id = fields.Many2one(
        comodel_name='ir.ui.menu', string='Submenú', readonly=True,
        copy=False, ondelete='set null',
        help="Submenú generado en el menú lateral, con los tipos de "
             "registro de este grupo colgando debajo.")

    def write(self, vals):
        res = super().write(vals)
        if 'name' in vals:
            for grupo in self.filtered('menu_id'):
                grupo.menu_id.name = grupo.name
        return res

    def unlink(self):
        self.mapped('menu_id').sudo().unlink()
        return super().unlink()
