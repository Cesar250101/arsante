# -*- coding: utf-8 -*-
"""Agrega «Nombre Fabricante» al tipo Revisión OC Cosméticos.

Reutiliza la columna compartida ``x_arsante_fabricante_id`` (many2one a
res.partner), ya usada por otros tipos del dominio cosméticos.
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    tipo = env.ref('arsante.revision_oc_cosmeticos_id',
                    raise_if_not_found=False)
    if not tipo:
        return

    Campo = env['arsante.campo'].sudo()
    if Campo.with_context(active_test=False).search([
        ('tipo_registro_id', '=', tipo.id), ('code', '=', 'fabricante_id'),
    ]):
        return  # ya existe (idempotente)

    Campo.create({
        'tipo_registro_id': tipo.id,
        'name': 'Nombre Fabricante',
        'code': 'fabricante_id',
        'ttype': 'many2one',
        'comodel_name': 'res.partner',
        'seccion': 'izq',
        'sequence': 70,
        'mostrar_en_formulario': True,
        'mostrar_en_lista': True,
        'mostrar_en_busqueda': True,
    })
    env['arsante.registro'].clear_caches()
    _logger.info("arsante: agregado fabricante_id a Revisión OC Cosméticos "
                 "(tipo_registro_id=%d)", tipo.id)
