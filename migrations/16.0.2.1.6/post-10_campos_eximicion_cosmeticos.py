# -*- coding: utf-8 -*-
"""Agrega Nro. OC, Nombre ISP Producto y Correos Electrónicos a Eximición
Cosméticos.

- ``correo_ids`` ya existe como columna compartida (``x_arsante_correo_ids``,
  char); en este tipo la tabla legacy la tenía 100% vacía, por eso el catálogo
  de 16.0.2.0.0 la había descartado. Se reutiliza la misma columna.
- ``nro_oc`` también existía en 4 tablas legacy (registro_desinfectantes,
  registro_dispositivos_medicos, renovaciones_desinfectantes,
  rev_antecedentes_dm), pero 100% vacía en las cuatro, así que nunca llegó a
  crearse ni ahí ni aquí. Se crea ahora por primera vez.
- ``producto_id`` es un campo nuevo (nunca existió en ninguna tabla legacy):
  texto libre para el nombre del producto tal como quedó registrado ante el
  ISP, distinto del campo núcleo «Producto» (product_id), que es la ficha de
  Odoo.
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

CAMPOS = [
    {'code': 'nro_oc', 'name': 'Nro. OC', 'ttype': 'char', 'sequence': 60},
    {'code': 'producto_id', 'name': 'Nombre ISP Producto', 'ttype': 'char',
     'sequence': 61},
    {'code': 'correo_ids', 'name': 'Correos Electrónicos', 'ttype': 'char',
     'sequence': 62},
]


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    tipo = env.ref('arsante.eximiciones_cosmeticos_id',
                    raise_if_not_found=False)
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
    _logger.info("arsante: agregados %d campos a Eximición Cosméticos (%s)",
                 len(vals_list), ", ".join(v['code'] for v in vals_list))
