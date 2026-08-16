# -*- coding: utf-8 -*-
"""Agrega «Correos Electrónicos» al tipo Modificacion Cosmeticos.

Mismo caso que CDA Alimentos (16.0.2.1.4) e Inscripción Cosméticos
(16.0.2.1.7): la columna ``correo_ids`` existía en la tabla legacy
(``arsante_modificacion_cosmeticos``) pero 100% vacía, así que el catálogo de
16.0.2.0.0 la había descartado. Se reutiliza la columna compartida
``x_arsante_correo_ids``.
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    tipo = env.ref('arsante.modificacion_cosmeticos_id',
                    raise_if_not_found=False)
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
        'sequence': 60,
        'mostrar_en_formulario': True,
        'mostrar_en_lista': True,
        'mostrar_en_busqueda': True,
    })
    env['arsante.registro'].clear_caches()
    _logger.info("arsante: agregado correo_ids a Modificacion Cosmeticos "
                 "(tipo_registro_id=%d)", tipo.id)
