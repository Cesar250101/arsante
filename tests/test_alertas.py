# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestAlertasArsante(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Alerta = self.env['arsante.alerta']
        self.Historial = self.env['arsante.alerta.historial']
        self.Registro = self.env['arsante.registro']
        self._contador = 0

    def _crear_tipo(self):
        self._contador += 1
        return self.env['arsante.tipo_registro'].create({
            'name': 'Tipo alerta %s' % self._contador,
            'code': 'tipo_alerta_%s' % self._contador,
        })

    @staticmethod
    def _campo(tipo, code):
        return tipo.campo_ids.filtered(lambda campo: campo.code == code)

    def _crear_registro(self, tipo, fecha, email='cliente@example.com'):
        partner = self.env['res.partner'].create({
            'name': 'Cliente de prueba',
            'email': email,
        })
        return self.Registro.create({
            'tipo_registro_id': tipo.id,
            'partner_id': partner.id,
            'fecha_renovacion': fecha,
        })

    def test_alerta_fecha_generates_one_daily_notification(self):
        tipo = self._crear_tipo()
        alerta = self.Alerta.create({
            'tipo_registro_id': tipo.id,
            'campo_id': self._campo(tipo, 'fecha_renovacion').id,
            'dias_anticipacion': 3,
        })
        today = fields.Date.context_today(self.Alerta)
        registro = self._crear_registro(tipo, today + timedelta(days=2))

        self.Alerta._cron_procesar_alertas()
        historial = self.Historial.search([
            ('alerta_id', '=', alerta.id), ('registro_id', '=', registro.id),
        ])
        self.assertEqual(historial.ultima_notificacion_fecha, today)
        mensajes = registro.message_ids.filtered(
            lambda message: 'Alerta de' in (message.body or ''))
        self.assertEqual(len(mensajes), 1)

        # Una segunda ejecución el mismo día no debe duplicar el aviso.
        self.Alerta._cron_procesar_alertas()
        mensajes = registro.message_ids.filtered(
            lambda message: 'Alerta de' in (message.body or ''))
        self.assertEqual(len(mensajes), 1)

    def test_expired_date_is_not_discarded_and_new_date_opens_cycle(self):
        tipo = self._crear_tipo()
        alerta = self.Alerta.create({
            'tipo_registro_id': tipo.id,
            'campo_id': self._campo(tipo, 'fecha_renovacion').id,
            'dias_anticipacion': 0,
        })
        today = fields.Date.context_today(self.Alerta)
        registro = self._crear_registro(tipo, today - timedelta(days=1))

        self.Alerta._cron_procesar_alertas()
        historial = self.Historial.search([
            ('alerta_id', '=', alerta.id), ('registro_id', '=', registro.id),
            ('fecha_alertada', '=', today - timedelta(days=1)),
        ])
        self.assertTrue(historial)

        # Una fecha nueva, al alcanzar el umbral, tiene su propio historial.
        registro.fecha_renovacion = today
        self.Alerta._cron_procesar_alertas()
        self.assertEqual(self.Historial.search_count([
            ('alerta_id', '=', alerta.id), ('registro_id', '=', registro.id),
        ]), 2)

    def test_dynamic_date_field_can_activate_alert(self):
        tipo = self._crear_tipo()
        campo = self.env['arsante.campo'].create({
            'tipo_registro_id': tipo.id,
            'name': 'Fecha de vencimiento de prueba',
            'code': 'fecha_vencimiento_prueba_%s' % self._contador,
            'ttype': 'date',
            'seccion': 'izq',
        })
        alerta = self.Alerta.create({
            'tipo_registro_id': tipo.id,
            'campo_id': campo.id,
            'dias_anticipacion': 1,
        })
        today = fields.Date.context_today(self.Alerta)
        registro = self._crear_registro(tipo, False)
        registro[campo.field_name] = today + timedelta(days=1)

        self.Alerta._cron_procesar_alertas()
        self.assertTrue(self.Historial.search([
            ('alerta_id', '=', alerta.id), ('registro_id', '=', registro.id),
            ('fecha_alertada', '=', today + timedelta(days=1)),
        ]))

    def test_email_is_queued_once_per_date_cycle(self):
        tipo = self._crear_tipo()
        template = self.env['mail.template'].create({
            'name': 'Alerta Arsante de prueba',
            'model_id': self.env['ir.model']._get('arsante.registro').id,
            'subject': 'Alerta Arsante de prueba',
            'body_html': '<p>Alerta de prueba</p>',
        })
        alerta = self.Alerta.create({
            'tipo_registro_id': tipo.id,
            'campo_id': self._campo(tipo, 'fecha_renovacion').id,
            'dias_anticipacion': 0,
            'avisar_correo_cliente': True,
            'email_template_id': template.id,
        })
        registro = self._crear_registro(tipo, fields.Date.context_today(self.Alerta))

        self.Alerta._cron_procesar_alertas()
        historial = self.Historial.search([
            ('alerta_id', '=', alerta.id), ('registro_id', '=', registro.id),
        ])
        self.assertTrue(historial.correo_enviado_en)
        self.assertEqual(self.env['mail.mail'].search_count([
            ('subject', '=', 'Alerta Arsante de prueba'),
            ('email_to', '=', registro.partner_id.email),
        ]), 1)

        self.Alerta._cron_procesar_alertas()
        self.assertEqual(self.env['mail.mail'].search_count([
            ('subject', '=', 'Alerta Arsante de prueba'),
            ('email_to', '=', registro.partner_id.email),
        ]), 1)

        sin_correo = self._crear_registro(
            tipo, fields.Date.context_today(self.Alerta), email=False)
        self.Alerta._cron_procesar_alertas()
        historial_sin_correo = self.Historial.search([
            ('alerta_id', '=', alerta.id), ('registro_id', '=', sin_correo.id),
        ])
        self.assertTrue(historial_sin_correo.ultima_notificacion_fecha)
        self.assertFalse(historial_sin_correo.correo_enviado_en)

    def test_invalid_alert_configuration_is_rejected(self):
        tipo = self._crear_tipo()
        fecha = self._campo(tipo, 'fecha_renovacion')
        campo_no_fecha = self._campo(tipo, 'partner_id')

        with self.assertRaises(ValidationError):
            self.Alerta.create({
                'tipo_registro_id': tipo.id,
                'campo_id': fecha.id,
                'dias_anticipacion': -1,
            })
        with self.assertRaises(ValidationError):
            self.Alerta.create({
                'tipo_registro_id': tipo.id,
                'campo_id': campo_no_fecha.id,
                'dias_anticipacion': 0,
            })
        with self.assertRaises(ValidationError):
            self.Alerta.create({
                'tipo_registro_id': tipo.id,
                'campo_id': fecha.id,
                'dias_anticipacion': 0,
                'avisar_correo_cliente': True,
            })
