# -*- coding: utf-8 -*-
"""Asistente para la asignación explícita de registros Arsante."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class ArsanteRegistroAsignar(models.TransientModel):
    _name = 'arsante.registro.asignar'
    _description = 'Asignar registro Arsante'

    registro_ids = fields.Many2many(
        comodel_name='arsante.registro', string='Registros', required=True,
        readonly=True)
    company_id = fields.Many2one(
        comodel_name='res.company', string='Compañía', required=True,
        readonly=True, default=lambda self: self.env.company)
    usuario_id = fields.Many2one(
        comodel_name='res.users', string='Asignar a', required=True,
        domain=lambda self: self._domain_usuarios_asignables(),
        help='Se muestran los usuarios internos activos de la compañía actual.')

    @api.model
    def _domain_usuarios_asignables(self):
        return self.env['arsante.registro']._domain_usuarios_asignables()

    @api.constrains('usuario_id', 'company_id')
    def _check_usuario_asignable(self):
        for wizard in self:
            usuario = wizard.usuario_id.sudo()
            if usuario and (not usuario.active or usuario.share):
                raise ValidationError(_(
                    'El usuario seleccionado debe ser un usuario interno '
                    'activo.'))
            if (usuario and wizard.company_id
                    and wizard.company_id not in usuario.company_ids):
                raise ValidationError(_(
                    'El usuario seleccionado debe pertenecer a la compañía '
                    'actual.'))

    def action_asignar(self):
        self.ensure_one()
        if not self.env['arsante.registro']._puede_asignar_registro():
            raise AccessError(_(
                'Solo los administradores Arsante o usuarios con permisos de '
                'Ajustes pueden asignar registros.'))
        self.registro_ids.write({'assigned_user_id': self.usuario_id.id})
        return {'type': 'ir.actions.act_window_close'}
