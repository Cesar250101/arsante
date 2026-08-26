# -*- coding: utf-8 -*-
"""Configuración acotada del grupo ``arsante.administrador``."""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ArsanteAdministrador(models.Model):
    _name = 'arsante.administrador'
    _description = 'Grupo Administrador Arsante'

    name = fields.Char(string='Nombre', required=True, readonly=True)
    usuario_ids = fields.Many2many(
        comodel_name='res.users', string='Usuarios administradores',
        compute='_compute_usuario_ids', inverse='_inverse_usuario_ids',
        help='Solo estos usuarios pueden recibir asignaciones y eliminar '
             'registros Arsante.')

    @api.depends_context('uid')
    def _compute_usuario_ids(self):
        grupo = self.env.ref('arsante.group_arsante_administrador',
                             raise_if_not_found=False)
        usuarios = grupo.users if grupo else self.env['res.users']
        for configuracion in self:
            configuracion.usuario_ids = usuarios

    def _inverse_usuario_ids(self):
        grupo = self.env.ref('arsante.group_arsante_administrador')
        for configuracion in self:
            if not configuracion.usuario_ids:
                raise ValidationError(_(
                    'El grupo Administrador debe conservar al menos un usuario.'))
            # El formulario está deliberadamente disponible sin conceder a
            # arsante.administrador acceso global a Ajustes/res.groups.
            grupo.sudo().write({'users': [(6, 0, configuracion.usuario_ids.ids)]})
