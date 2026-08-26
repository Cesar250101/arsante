# -*- coding: utf-8 -*-
"""Agrega Nº OC y Correos Electrónicos a Inscripción Cosméticos.

Ninguno de los dos tenía columna en la tabla legacy de este tipo
(``arsante_inscripciones_cosmeticos``). Ambos códigos ya existen como
columnas compartidas (``x_arsante_nro_oc`` desde 16.0.2.1.6,
``x_arsante_correo_ids`` desde 16.0.2.0.0): se reutilizan, no se crean
columnas nuevas.
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

CAMPOS = [
    {'code': 'nro_oc', 'name': 'Nro. OC', 'ttype': 'char', 'sequence': 60},
    {'code': 'correo_ids', 'name': 'Correos Electrónicos', 'ttype': 'char',
     'sequence': 61},
]


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    tipo = env.ref('arsante.inscripciones_id', raise_if_not_found=False)
    if not tipo:
        return

    Campo = env['arsante.campo'].sudo()
    existentes = set(Campo.with_context(active_test=False).search(
        [('tipo_registro_id', '=', tipo.id)]).mapped('code'))

    vals_list = []
    for datos in CAMPOS:
        if datos['code'] in existentes:
            continue
        vals_list.append({
            'tipo_registro_id': tipo.id,
            'name': datos['name'],
            'code': datos['code'],
            'ttype': datos['ttype'],
            'seccion': 'izq',
            'sequence': datos['sequence'],
            'mostrar_en_formulario': True,
            'mostrar_en_lista': True,
            'mostrar_en_busqueda': True,
        })
    if not vals_list:
        return

    Campo.create(vals_list)
    env['arsante.registro'].clear_caches()
    _logger.info("arsante: agregados %d campos a Inscripción Cosméticos (%s)",
                 len(vals_list), ", ".join(v['code'] for v in vals_list))
