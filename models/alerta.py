# -*- coding: utf-8 -*-
"""Alertas configurables para los registros Arsante.

Cada alerta observa un campo de tipo Fecha de un tipo de registro. El cron
diario guarda un historial por valor de fecha, de modo que una renovación abre
un ciclo nuevo y una doble ejecución del cron no duplica avisos.
"""

import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import html_escape

_logger = logging.getLogger(__name__)


class ArsanteAlerta(models.Model):
    _name = 'arsante.alerta'
    _description = 'Alerta de Tipo de Registro Arsante'
    _order = 'tipo_registro_id, campo_id, id'

    tipo_registro_id = fields.Many2one(
        comodel_name='arsante.tipo_registro', string='Tipo de Registro',
        required=True, ondelete='cascade', index=True)
    campo_id = fields.Many2one(
        comodel_name='arsante.campo', string='Campo de fecha', required=True,
        ondelete='cascade', index=True,
        domain="[('ttype', '=', 'date'), ('active', '=', True)]")
    dias_anticipacion = fields.Integer(
        string='Días antes de avisar', required=True, default=0,
        help='Cantidad de días antes de la fecha en que comienza la alerta.')
    avisar_correo_cliente = fields.Boolean(string='Avisar correo al cliente')
    email_template_id = fields.Many2one(
        comodel_name='mail.template', string='Plantilla de correo',
        ondelete='restrict',
        domain="[('model', '=', 'arsante.registro')]",
        help='Plantilla aplicada al registro y enviada al email del cliente.')
    historial_ids = fields.One2many(
        comodel_name='arsante.alerta.historial', inverse_name='alerta_id',
        string='Historial', readonly=True)

    _sql_constraints = [
        ('tipo_campo_uniq', 'unique(tipo_registro_id, campo_id)',
         'Ya existe una alerta para este campo de fecha.'),
    ]

    @api.constrains('tipo_registro_id', 'campo_id')
    def _check_campo(self):
        for alerta in self:
            campo = alerta.campo_id
            if not campo:
                continue
            if campo.tipo_registro_id != alerta.tipo_registro_id:
                raise ValidationError(_(
                    'El campo de fecha debe pertenecer al mismo tipo de registro.'))
            if campo.ttype != 'date':
                raise ValidationError(_(
                    'Solo se pueden configurar alertas sobre campos de tipo Fecha.'))
            if not campo.active:
                raise ValidationError(_(
                    'No se puede configurar una alerta sobre un campo archivado.'))

    @api.constrains('dias_anticipacion')
    def _check_dias_anticipacion(self):
        for alerta in self:
            if alerta.dias_anticipacion < 0:
                raise ValidationError(_(
                    'Los días antes de avisar deben ser cero o un número positivo.'))

    @api.constrains('avisar_correo_cliente', 'email_template_id')
    def _check_plantilla_correo(self):
        for alerta in self:
            plantilla = alerta.email_template_id
            if alerta.avisar_correo_cliente and not plantilla:
                raise ValidationError(_(
                    'Seleccione una plantilla para avisar por correo al cliente.'))
            if plantilla and plantilla.model != 'arsante.registro':
                raise ValidationError(_(
                    'La plantilla de correo debe aplicarse a Registros Arsante.'))

    @api.model
    def _cron_procesar_alertas(self):
        """Envía los avisos internos y el primer correo de cada ciclo.

        La fecha de alerta se guarda en el historial. Si el usuario renueva un
        registro, el valor de fecha cambia y el próximo umbral genera otra fila
        de historial, habilitando una nueva notificación y correo.
        """
        hoy = fields.Date.context_today(self)
        destinatarios = self._partner_ids_usuarios_arsante()
        Registro = self.env['arsante.registro'].sudo()
        Historial = self.env['arsante.alerta.historial'].sudo()

        for alerta in self.sudo().search([]):
            campo = alerta.campo_id
            # Una regla inválida no debe detener las demás alertas. Las
            # constraints impiden este estado normalmente, pero la revisión
            # protege datos antiguos o modificaciones hechas por SQL.
            if (not campo.active or campo.ttype != 'date'
                    or campo.tipo_registro_id != alerta.tipo_registro_id
                    or campo.field_name not in Registro._fields):
                _logger.warning(
                    'arsante: alerta %s ignorada por campo inválido', alerta.id)
                continue

            limite = hoy + timedelta(days=alerta.dias_anticipacion)
            registros = Registro.search([
                ('tipo_registro_id', '=', alerta.tipo_registro_id.id),
                ('active', '=', True),
                (campo.field_name, '!=', False),
                (campo.field_name, '<=', limite),
            ])
            for registro in registros:
                fecha_alertada = registro[campo.field_name]
                historial = Historial.search([
                    ('alerta_id', '=', alerta.id),
                    ('registro_id', '=', registro.id),
                    ('fecha_alertada', '=', fecha_alertada),
                ], limit=1)
                if not historial:
                    historial = Historial.create({
                        'alerta_id': alerta.id,
                        'registro_id': registro.id,
                        'fecha_alertada': fecha_alertada,
                    })

                if historial.ultima_notificacion_fecha != hoy:
                    try:
                        registro.with_context(
                            mail_create_nosubscribe=True).message_post(
                            body=alerta._mensaje_alerta(registro, fecha_alertada),
                            message_type='notification',
                            partner_ids=destinatarios,
                        )
                        historial.ultima_notificacion_fecha = hoy
                    except Exception:
                        _logger.exception(
                            'arsante: no se pudo publicar alerta %s del registro %s',
                            alerta.id, registro.id)

                if (alerta.avisar_correo_cliente
                        and not historial.correo_enviado_en
                        and registro.partner_id.email):
                    try:
                        alerta.email_template_id.sudo().send_mail(
                            registro.id,
                            force_send=False,
                            email_values={'email_to': registro.partner_id.email},
                        )
                        historial.correo_enviado_en = fields.Datetime.now()
                    except Exception:
                        _logger.exception(
                            'arsante: no se pudo encolar correo de alerta %s '
                            'para el registro %s', alerta.id, registro.id)
        return True

    @api.model
    def _partner_ids_usuarios_arsante(self):
        """Partners activos de los usuarios que deben recibir el inbox."""
        grupo = self.env.ref('arsante.group_arsante_users',
                             raise_if_not_found=False)
        if not grupo:
            _logger.warning('arsante: no existe el grupo de usuarios Arsante')
            return []
        return grupo.users.filtered('active').mapped('partner_id').ids

    def _mensaje_alerta(self, registro, fecha_alertada):
        self.ensure_one()
        return _(
            '<p><strong>Alerta de %(tipo)s</strong></p>'
            '<p>El registro <strong>%(registro)s</strong> tiene '
            '<strong>%(campo)s</strong> programada para %(fecha)s.</p>',
            tipo=html_escape(self.tipo_registro_id.display_name),
            registro=html_escape(registro.display_name),
            campo=html_escape(self.campo_id.name),
            fecha=fields.Date.to_string(fecha_alertada),
        )


class ArsanteAlertaHistorial(models.Model):
    _name = 'arsante.alerta.historial'
    _description = 'Historial de Alerta Arsante'
    _order = 'fecha_alertada desc, id desc'

    alerta_id = fields.Many2one(
        comodel_name='arsante.alerta', string='Alerta', required=True,
        ondelete='cascade', index=True)
    registro_id = fields.Many2one(
        comodel_name='arsante.registro', string='Registro', required=True,
        ondelete='cascade', index=True)
    fecha_alertada = fields.Date(string='Fecha alertada', required=True,
                                  index=True)
    ultima_notificacion_fecha = fields.Date(
        string='Última notificación interna', readonly=True)
    correo_enviado_en = fields.Datetime(string='Correo encolado el', readonly=True)

    _sql_constraints = [
        ('alerta_registro_fecha_uniq',
         'unique(alerta_id, registro_id, fecha_alertada)',
         'Ya existe un historial para esta alerta, registro y fecha.'),
    ]
