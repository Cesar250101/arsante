# -*- coding: utf-8 -*-
"""Asistentes para operaciones destructivas sobre campos dinámicos.

Odoo permite renombrar un campo manual (hace ALTER TABLE ... RENAME COLUMN) pero
NO permite cambiar su tipo de dato (ir_model.py: "Changing the type of a field is
not yet supported"). Cambiar el tipo implica crear una columna nueva, convertir
los valores y borrar la vieja, así que se hace por asistente y avisando de
cuántos valores se perderían.
"""

import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..models.campo import RE_CODE, TTYPES
from ..models.plantilla import nombre_tecnico

_logger = logging.getLogger(__name__)

# Conversiones cuyo valor se conserva. Cualquier otra combinación exige que el
# usuario acepte explícitamente la pérdida de los valores no convertibles.
CASTS = {
    ('char', 'text'): '"%(col)s"',
    ('text', 'char'): '"%(col)s"',
    ('char', 'integer'): "NULLIF(regexp_replace(\"%(col)s\", '[^0-9-]', '', 'g'), '')::integer",
    ('char', 'float'): "NULLIF(regexp_replace(\"%(col)s\", '[^0-9.-]', '', 'g'), '')::numeric",
    ('integer', 'char'): '"%(col)s"::varchar',
    ('integer', 'float'): '"%(col)s"::numeric',
    ('float', 'integer'): 'round("%(col)s")::integer',
    ('float', 'char'): '"%(col)s"::varchar',
    ('char', 'selection'): '"%(col)s"',
    ('selection', 'char'): '"%(col)s"',
    ('char', 'date'): "NULLIF(\"%(col)s\", '')::date",
    ('date', 'char'): '"%(col)s"::varchar',
    ('date', 'datetime'): '"%(col)s"::timestamp',
    ('datetime', 'date'): '"%(col)s"::date',
}


class ArsanteCampoRenombrar(models.TransientModel):
    _name = 'arsante.campo.renombrar'
    _description = 'Renombrar código de campo'

    campo_id = fields.Many2one(
        comodel_name='arsante.campo', string='Campo', required=True,
        readonly=True)
    code_actual = fields.Char(related='campo_id.code', string='Código actual',
                              readonly=True)
    code_nuevo = fields.Char(string='Nuevo código', required=True)
    compartido_con = fields.Char(
        string='Atención', compute='_compute_compartido_con', readonly=True)

    @api.depends('campo_id')
    def _compute_compartido_con(self):
        for wiz in self:
            otros = self.env['arsante.campo'].search([
                ('code', '=', wiz.campo_id.code),
                ('id', '!=', wiz.campo_id.id),
            ])
            if otros:
                wiz.compartido_con = _(
                    "Este campo comparte columna con los tipos: %s. "
                    "Renombrarlo los afecta a todos.",
                    ", ".join(otros.mapped('tipo_registro_id.name')))
            else:
                wiz.compartido_con = False

    def action_renombrar(self):
        self.ensure_one()
        campo = self.campo_id
        nuevo = (self.code_nuevo or '').strip().lower()

        if not RE_CODE.match(nuevo):
            raise UserError(_(
                "El código «%s» no es válido: debe empezar por una letra "
                "minúscula y usar solo minúsculas, números y guiones bajos.",
                nuevo))
        if nuevo == campo.code:
            raise UserError(_("El código nuevo es igual al actual."))
        if nuevo in self.env['arsante.registro']._fields:
            raise UserError(_(
                "«%s» ya es un campo estándar del registro.", nuevo))

        nuevo_tecnico = nombre_tecnico(nuevo)
        if self.env['ir.model.fields'].sudo().search_count([
                ('model', '=', 'arsante.registro'), ('name', '=', nuevo_tecnico)]):
            raise UserError(_(
                "Ya existe un campo con el código «%s».", nuevo))

        hermanos = self.env['arsante.campo'].search([('code', '=', campo.code)])
        antiguo = campo.code

        # Odoo hace el ALTER TABLE ... RENAME COLUMN, un campo por transacción.
        campo.ir_field_id.sudo().write({'name': nuevo_tecnico})
        hermanos.with_context(arsante_via_wizard=True).write({'code': nuevo})

        self._reescribir_plantillas(antiguo, nuevo)
        self.env['arsante.registro'].clear_caches()

        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def _reescribir_plantillas(self, antiguo, nuevo):
        """Las plantillas referencian los códigos: hay que actualizarlas o
        dejarían de resolver y las líneas de venta saldrían incompletas."""
        patron = re.compile(r'\{%s\}' % re.escape(antiguo))
        campos_txt = ('name_template', 'so_line_template')
        campos_csv = ('so_required_codes', 'so_oc_codes', 'so_product_code',
                      'so_marca_code')
        for tipo in self.env['arsante.tipo_registro'].search([]):
            vals = {}
            for nombre in campos_txt:
                valor = tipo[nombre]
                if valor and patron.search(valor):
                    vals[nombre] = patron.sub('{%s}' % nuevo, valor)
            for nombre in campos_csv:
                valor = tipo[nombre]
                if valor:
                    partes = [nuevo if p.strip() == antiguo else p.strip()
                              for p in valor.split(',')]
                    if partes != [p.strip() for p in valor.split(',')]:
                        vals[nombre] = ','.join(partes)
            if vals:
                tipo.write(vals)


class ArsanteCampoConvertir(models.TransientModel):
    _name = 'arsante.campo.convertir'
    _description = 'Convertir tipo de dato de un campo'

    campo_id = fields.Many2one(
        comodel_name='arsante.campo', string='Campo', required=True,
        readonly=True)
    ttype_actual = fields.Selection(
        related='campo_id.ttype', string='Tipo actual', readonly=True)
    ttype_nuevo = fields.Selection(
        selection=TTYPES, string='Nuevo tipo', required=True)
    comodel_name = fields.Selection(
        selection=lambda self: self.env['arsante.campo']._fields['comodel_name'].selection,
        string='Relacionado con')

    valores_totales = fields.Integer(
        string='Valores guardados', compute='_compute_impacto', readonly=True)
    valores_perdidos = fields.Integer(
        string='Valores que se perderían', compute='_compute_impacto',
        readonly=True)
    acepto = fields.Boolean(
        string='Entiendo que se perderán los valores indicados')

    @api.depends('campo_id', 'ttype_nuevo')
    def _compute_impacto(self):
        for wiz in self:
            wiz.valores_totales = wiz.campo_id._contar_valores() if wiz.campo_id else 0
            wiz.valores_perdidos = 0
            if not (wiz.campo_id and wiz.ttype_nuevo) or not wiz.valores_totales:
                continue
            cast = CASTS.get((wiz.campo_id.ttype, wiz.ttype_nuevo))
            if not cast:
                wiz.valores_perdidos = wiz.valores_totales
                continue
            columna = wiz.campo_id.field_name
            try:
                # Savepoint y no rollback: en PostgreSQL un error de SQL aborta
                # la transacción entera, y un rollback aquí desharía todo lo que
                # el usuario llevara hecho en esta petición.
                with self.env.cr.savepoint():
                    self.env.cr.execute(
                        'SELECT count(*) FROM arsante_registro '
                        'WHERE "%(col)s" IS NOT NULL AND (%(cast)s) IS NULL'
                        % {'col': columna, 'cast': cast % {'col': columna}})
                    wiz.valores_perdidos = self.env.cr.fetchone()[0]
            except Exception:
                # Un cast que ni siquiera se puede evaluar: se pierde todo.
                wiz.valores_perdidos = wiz.valores_totales

    def action_convertir(self):
        self.ensure_one()
        campo = self.campo_id
        if self.ttype_nuevo == campo.ttype:
            raise UserError(_("El tipo nuevo es igual al actual."))
        if self.valores_perdidos and not self.acepto:
            raise UserError(_(
                "La conversión perdería %(n)s de %(t)s valores. Marque la "
                "casilla de confirmación si desea continuar.",
                n=self.valores_perdidos, t=self.valores_totales))
        if self.ttype_nuevo == 'many2one' and not self.comodel_name:
            raise UserError(_("Indique con qué modelo se relaciona el campo."))

        hermanos = self.env['arsante.campo'].search([('code', '=', campo.code)])
        columna = campo.field_name
        temporal = '%s_tmp' % columna
        cast = CASTS.get((campo.ttype, self.ttype_nuevo))

        with self.env.cr.savepoint():
            IrField = self.env['ir.model.fields'].sudo()
            model_id = self.env['ir.model']._get_id('arsante.registro')

            vals_tmp = {
                'model_id': model_id, 'name': temporal,
                'field_description': '%s (temporal)' % campo.name,
                'ttype': self.ttype_nuevo, 'state': 'manual', 'store': True,
                'required': False, 'readonly': False,
            }
            if self.ttype_nuevo == 'many2one':
                vals_tmp.update({'relation': self.comodel_name,
                                 'on_delete': 'set null'})
            campo_tmp = IrField.create(vals_tmp)

            if cast:
                self.env.cr.execute(
                    'UPDATE arsante_registro SET "%(tmp)s" = (%(cast)s) '
                    'WHERE "%(col)s" IS NOT NULL'
                    % {'tmp': temporal, 'col': columna,
                       'cast': cast % {'col': columna}})

            campo.ir_field_id.sudo().unlink()          # DROP COLUMN CASCADE
            campo_tmp.write({'name': columna,
                             'field_description': campo.name})

            hermanos = hermanos.with_context(arsante_via_wizard=True)
            hermanos.write({'ttype': self.ttype_nuevo,
                            'comodel_name': self.comodel_name or False})
            hermanos.write({'ir_field_id': campo_tmp.id})

        self.env['arsante.registro'].clear_caches()
        _logger.info("arsante: campo %s convertido de %s a %s (%d valores perdidos)",
                     columna, self.ttype_actual, self.ttype_nuevo,
                     self.valores_perdidos)
        return {'type': 'ir.actions.client', 'tag': 'reload'}
