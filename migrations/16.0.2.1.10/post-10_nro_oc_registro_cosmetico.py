# -*- coding: utf-8 -*-
"""Agrega «Nro. OC» al tipo Registro Cosmeticos.

No estaba en la vista legacy de este tipo (nunca se usó ahí); se agrega para
uso a partir de ahora, reutilizando la columna compartida ``x_arsante_nro_oc``
(creada en 16.0.2.1.6 para Eximición Cosméticos).
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    tipo = env.ref('arsante.registro_cosmetico_id', raise_if_not_found=False)
    if not tipo:
        return

    Campo = env['arsante.campo'].sudo()
    if Campo.with_context(active_test=False).search([
        ('tipo_registro_id', '=', tipo.id), ('code', '=', 'nro_oc'),
    ]):
        return  # ya existe (idempotente)

    Campo.create({
        'tipo_registro_id': tipo.id,
        'name': 'Nro. OC',
        'code': 'nro_oc',
        'ttype': 'char',
        'seccion': 'izq',
        'sequence': 61,
        'mostrar_en_formulario': True,
        'mostrar_en_lista': True,
        'mostrar_en_busqueda': True,
    })
    env['arsante.registro'].clear_caches()
    _logger.info("arsante: agregado nro_oc a Registro Cosmeticos "
                 "(tipo_registro_id=%d)", tipo.id)
