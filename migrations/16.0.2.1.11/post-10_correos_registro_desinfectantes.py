# -*- coding: utf-8 -*-
"""Agrega «Correos Electrónicos» al tipo Registro Desinfectantes.

La vista legacy de este tipo tenía un campo «correos» (no «correo_ids» como
los demás), pero su columna en la tabla legacy (``arsante_registro_desinfectantes``)
tiene 0 valores en los 6 registros existentes: no hay nada que recuperar. Se
usa el código compartido ``correo_ids`` (no «correos») para que quede
agrupable y filtrable junto con los otros 7 tipos que ya lo tienen, en vez de
crear una columna nueva y aislada.
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    tipo = env.ref('arsante.registro_desinfectantes_id',
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
        'sequence': 66,
        'mostrar_en_formulario': True,
        'mostrar_en_lista': True,
        'mostrar_en_busqueda': True,
    })
    env['arsante.registro'].clear_caches()
    _logger.info("arsante: agregado correo_ids a Registro Desinfectantes "
                 "(tipo_registro_id=%d)", tipo.id)
