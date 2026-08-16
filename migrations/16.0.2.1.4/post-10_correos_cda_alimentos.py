# -*- coding: utf-8 -*-
"""Agrega «Correos Electrónicos» al tipo CDA Alimentos.

El código ``correo_ids`` ya existe como columna compartida
(``x_arsante_correo_ids``, char): la usan CDA Cosméticos, Dispositivos
Médicos, Registro Dispositivos Médicos y Declaración Dispositivos Médicos.
CDA Alimentos se quedó fuera porque en su tabla legacy
(``arsante_cda_uyd_alimentos``) la columna estaba 100% vacía y el catálogo de
la migración 16.0.2.0.0 descarta las columnas sin ningún valor real — no es
un error de esa migración, es que nunca se había usado ahí. Se añade ahora
para uso a partir de aquí; no hay datos históricos que recuperar.

Reutiliza la columna existente: al crear el ``arsante.campo`` con el mismo
código y tipo, ``_sync_ir_field`` la enlaza en vez de crear una nueva.
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    tipo = env.ref('arsante.cda_uyd_alimento_id', raise_if_not_found=False)
    if not tipo:
        return

    Campo = env['arsante.campo'].sudo()
    if Campo.with_context(active_test=False).search([
        ('tipo_registro_id', '=', tipo.id), ('code', '=', 'correo_ids'),
    ]):
        return  # ya existe (idempotente)

    Campo.create({
        'tipo_registro_id': tipo.id,
        'name': 'Correos Electrónicos',
        'code': 'correo_ids',
        'ttype': 'char',
        'seccion': 'izq',
        'sequence': 33,
        'mostrar_en_formulario': True,
        'mostrar_en_lista': True,
        'mostrar_en_busqueda': True,
    })
    env['arsante.registro'].clear_caches()
    _logger.info("arsante: agregado correo_ids a CDA Alimentos "
                 "(tipo_registro_id=%d)", tipo.id)
