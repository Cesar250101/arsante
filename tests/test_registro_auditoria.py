# -*- coding: utf-8 -*-

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase


class TestRegistroAuditoria(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Registro = self.env['arsante.registro']
        self._contador = 0
        self.admin_group = self.env.ref('arsante.group_arsante_administrador')
        self.user_group = self.env.ref('arsante.group_arsante_users')

    def _crear_tipo(self):
        self._contador += 1
        return self.env['arsante.tipo_registro'].create({
            'name': 'Tipo auditoría %s' % self._contador,
            'code': 'tipo_auditoria_%s' % self._contador,
        })

    def _crear_registro(self):
        tipo = self._crear_tipo()
        partner = self.env['res.partner'].create({'name': 'Cliente auditoría'})
        return self.Registro.create({
            'tipo_registro_id': tipo.id,
            'partner_id': partner.id,
        })

    def _crear_usuario(self, nombre, grupos):
        return self.env['res.users'].with_context(no_reset_password=True).create({
            'name': nombre,
            'login': '%s_%s@example.com' % (nombre.lower(), self._contador),
            'groups_id': [(6, 0, grupos.ids)],
        })

    def test_creation_and_write_are_registered_in_chatter(self):
        registro = self._crear_registro()
        creation = registro.message_ids.filtered(
            lambda message: 'Registro creado' in (message.body or ''))
        self.assertEqual(len(creation), 1)

        registro.write({'nro_resolucion': 'RES-123'})
        update = registro.message_ids.filtered(
            lambda message: 'Registro actualizado' in (message.body or ''))
        self.assertEqual(len(update), 1)
        self.assertIn('Nro. Resolución', update.body)
        self.assertIn('RES-123', update.body)

    def test_assignment_requires_internal_user_and_is_logged(self):
        registro = self._crear_registro()
        usuario = self._crear_usuario('Administrador', self.admin_group)
        registro.assigned_user_id = usuario

        assignment = registro.message_ids.filtered(
            lambda message: 'Registro asignado' in (message.body or ''))
        self.assertEqual(len(assignment), 1)
        self.assertIn(usuario.name, assignment.body)
        notification = registro.message_ids.filtered(
            lambda message: 'Se te ha asignado el registro' in (message.body or ''))
        self.assertEqual(len(notification), 1)
        inbox_notifications = notification.notification_ids.filtered(
            lambda item: item.res_partner_id == usuario.partner_id)
        self.assertEqual(len(inbox_notifications), 1)
        self.assertEqual(inbox_notifications.notification_type, 'inbox')
        self.assertFalse(inbox_notifications.is_read)

        usuario_normal = self._crear_usuario('Usuario normal', self.user_group)
        registro.assigned_user_id = usuario_normal
        self.assertEqual(registro.assigned_user_id, usuario_normal)

    def test_assignment_domain_is_limited_to_current_company(self):
        dominio = self.Registro._domain_usuarios_asignables()
        self.assertIn(('active', '=', True), dominio)
        self.assertIn(('share', '=', False), dominio)
        self.assertIn(
            ('company_ids', 'in', [self.env.company.id]),
            dominio,
        )

    def test_assignment_wizard_assigns_and_logs_in_chatter(self):
        registro = self._crear_registro()
        otro_registro = self._crear_registro()
        usuario = self._crear_usuario('Admin asistente', self.admin_group)
        wizard = self.env['arsante.registro.asignar'].create({
            'registro_ids': [(6, 0, (registro | otro_registro).ids)],
            'company_id': registro.company_id.id,
            'usuario_id': usuario.id,
        })

        wizard.action_asignar()

        self.assertEqual(registro.assigned_user_id, usuario)
        self.assertEqual(otro_registro.assigned_user_id, usuario)
        self.assertTrue(registro.message_ids.filtered(
            lambda message: 'Registro asignado' in (message.body or '')))

    def test_only_administrator_can_open_assignment_wizard(self):
        registro = self._crear_registro()
        user = self._crear_usuario('Sin asignación', self.user_group)
        with self.assertRaises(AccessError):
            registro.with_user(user).action_abrir_asignacion()

    def test_only_administrator_can_delete(self):
        registro = self._crear_registro()
        user = self._crear_usuario('Sin permisos', self.user_group)
        with self.assertRaises(AccessError):
            registro.with_user(user).unlink()

        admin = self._crear_usuario('Con permisos', self.admin_group)
        registro.with_user(admin).unlink()
        self.assertFalse(self.Registro.browse(registro.id).exists())

    def test_administrator_configuration_updates_group(self):
        configuracion = self.env.ref('arsante.arsante_administrador_config')
        usuario = self._crear_usuario('Nuevo admin', self.user_group)
        configuracion.usuario_ids = self.admin_group.users | usuario
        self.assertIn(usuario, self.admin_group.users)
