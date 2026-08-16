# -*- coding: utf-8 -*-
"""Agrega los campos de trabajo a CDA Dispositivos Medicos.

Este tipo nunca tuvo un modelo/tabla legacy propio (no está en
``arsante_backup``, ni tiene registro en ``data/tipo_registro.xml`` con
external ID: existe sólo como opción del selection ``tipo`` y sin ningún
registro creado todavía). Todos los códigos pedidos ya existen como columnas
compartidas usadas por los demás tipos del dominio «dispositivos médicos»
(Dispositivos Medicos, Registro Dispositivos Médicos): se reutilizan tal
cual, sin datos que migrar.
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

CAMPOS = [
    {'code': 'agente_aduana_id', 'name': 'Agente de Aduana',
     'ttype': 'many2one', 'comodel_name': 'res.partner'},
    {'code': 'ref_isp', 'name': 'Ref. ISP', 'ttype': 'char'},
    {'code': 'item', 'name': 'Item', 'ttype': 'char'},
    {'code': 'fecha_llegada', 'name': 'Fecha de Llegada', 'ttype': 'date'},
    {'code': 'proveedor_id', 'name': 'Proveedor', 'ttype': 'many2one',
     'comodel_name': 'res.partner'},
    {'code': 'nro_cda', 'name': 'Nro. CDA', 'ttype': 'char'},
    {'code': 'pdf_nro_resolucion', 'name': 'Pdf nro resolucion',
     'ttype': 'binary'},
    {'code': 'fecha_resolucion', 'name': 'Fecha Resolución', 'ttype': 'date'},
    {'code': 'cc_cesmec', 'name': 'Cc cesmec', 'ttype': 'char'},
    {'code': 'correo_ids', 'name': 'Correos Electrónicos', 'ttype': 'char'},
]


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    tipo = env['arsante.tipo_registro'].with_context(
        active_test=False).search(
        [('tipo', '=', 'cda_dispositivos_medicos')], limit=1)
    if not tipo:
        _logger.warning("arsante: tipo cda_dispositivos_medicos no "
                         "encontrado, se omite")
        return

    Campo = env['arsante.campo'].sudo()
    existentes = set(Campo.with_context(active_test=False).search(
        [('tipo_registro_id', '=', tipo.id)]).mapped('code'))

    vals_list = []
    for i, datos in enumerate(CAMPOS):
        if datos['code'] in existentes:
            continue
        vals_list.append({
            'tipo_registro_id': tipo.id,
            'name': datos['name'],
            'code': datos['code'],
            'ttype': datos['ttype'],
            'comodel_name': datos.get('comodel_name', False),
            'seccion': 'izq',
            'sequence': 10 + i,
            'mostrar_en_formulario': True,
            'mostrar_en_lista': True,
            'mostrar_en_busqueda': True,
        })
    if not vals_list:
        return

    Campo.create(vals_list)
    env['arsante.registro'].clear_caches()
    _logger.info("arsante: agregados %d campos a CDA Dispositivos Medicos "
                 "(%s)", len(vals_list), ", ".join(v['code'] for v in vals_list))
