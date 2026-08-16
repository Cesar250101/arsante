# -*- coding: utf-8 -*-
"""Agrega «Proveedor» y «Fecha de Llegada» al tipo Dispositivos Medicos.

Ambos códigos ya existen como columnas compartidas (``x_arsante_proveedor_id``
many2one a res.partner, ``x_arsante_fecha_llegada`` date): las usan CDA
Cosméticos, CDA Alimentos, UYD Alimentos y Registro Dispositivos Médicos. La
tabla legacy de este tipo (``arsante_dispositivos_medicos``) nunca tuvo esas
columnas, así que no hay datos históricos que recuperar; se agregan para uso
a partir de aquí.

Reutiliza las columnas existentes: al crear el ``arsante.campo`` con el mismo
código y tipo, ``_sync_ir_field`` las enlaza en vez de crear columnas nuevas.
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

CAMPOS = [
    {'code': 'proveedor_id', 'name': 'Proveedor', 'ttype': 'many2one',
     'comodel_name': 'res.partner', 'sequence': 35},
    {'code': 'fecha_llegada', 'name': 'Fecha de Llegada', 'ttype': 'date',
     'sequence': 36},
]


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    tipo = env.ref('arsante.dispositivos_medicos_id', raise_if_not_found=False)
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
            'comodel_name': datos.get('comodel_name', False),
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
    _logger.info("arsante: agregados %d campos a Dispositivos Medicos (%s)",
                 len(vals_list), ", ".join(v['code'] for v in vals_list))
