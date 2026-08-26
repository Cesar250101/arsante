# -*- coding: utf-8 -*-
"""Completa campos faltantes en 6 tipos con datos reales, detectados
comparando las vistas ``form`` legacy (qué campos diseñó el desarrollador
original para cada trámite) contra la configuración dinámica actual.

A diferencia del criterio de "columna 100% vacía" que usa post-30
(16.0.2.0.0), aquí el criterio es otro: un campo puede faltar aunque su
columna legacy nunca se haya llenado, simplemente porque el catálogo
automático sólo migra columnas con al menos un dato real. La vista, en
cambio, dice qué campos pertenecen al trámite independientemente de si se
usaron. Se aplica sólo a los tipos con registros reales; los 6 tipos sin
ningún registro (incluida Revisión OC Cosméticos) quedan pendientes a
propósito.

Se dejan fuera dos códigos dudosos que la vista legacy nombra distinto al
código ya establecido («correos» en vez de «correo_ids», «ref_SAFIS» en vez
de «ref_gicona» en Renovaciones Desinfectantes) hasta confirmarlos.

Todos los códigos reutilizan columnas compartidas ya existentes, salvo
``nro_renovacion`` y ``pdf_resolucion`` (nuevos, sólo en Declaración
Dispositivos Médicos, sin datos legacy que migrar).
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

# external_id de arsante.tipo_registro -> lista de campos a agregar
PLAN = {
    'arsante.registro_cosmetico_id': [
        {'code': 'correo_ids', 'name': 'Correos Electrónicos', 'ttype': 'char'},
    ],
    'arsante.registro_desinfectantes_id': [
        {'code': 'fabricante_id', 'name': 'Nombre Fabricante',
         'ttype': 'many2one', 'comodel_name': 'res.partner'},
        {'code': 'fecha_resolucion', 'name': 'Fecha Resolución', 'ttype': 'date'},
        {'code': 'marca', 'name': 'Marca', 'ttype': 'char'},
        {'code': 'nro_oc', 'name': 'Nro. OC', 'ttype': 'char'},
        {'code': 'pdf_nro_resolucion', 'name': 'Pdf nro resolucion',
         'ttype': 'binary'},
        {'code': 'ref_gicona', 'name': 'Ref. Gicona', 'ttype': 'char'},
    ],
    'arsante.renovaciones_cosmeticas_id': [
        {'code': 'correo_ids', 'name': 'Correos Electrónicos', 'ttype': 'char'},
    ],
    'arsante.uyd_alimentos_id': [
        {'code': 'correo_ids', 'name': 'Correos Electrónicos', 'ttype': 'char'},
        {'code': 'enviar_colilla_fecha', 'name': 'Enviar colilla fecha',
         'ttype': 'date'},
        {'code': 'exim_ctrl_calidad', 'name': 'Exim ctrl calidad',
         'ttype': 'char'},
    ],
    'arsante.registro_dispositivos_medicos_id': [
        {'code': 'fabricante_id', 'name': 'Nombre Fabricante',
         'ttype': 'many2one', 'comodel_name': 'res.partner'},
        {'code': 'nro_oc', 'name': 'Nro. OC', 'ttype': 'char'},
        {'code': 'nro_registro', 'name': 'Nro. Registro', 'ttype': 'char'},
        {'code': 'pdf_nro_resolucion', 'name': 'Pdf nro resolucion',
         'ttype': 'binary'},
        {'code': 'ref_gicona', 'name': 'Ref. Gicona', 'ttype': 'char'},
    ],
    'arsante.declaracion_dispositivos_medicos_id': [
        {'code': 'fecha_resolucion', 'name': 'Fecha Resolución', 'ttype': 'date'},
        {'code': 'nro_renovacion', 'name': 'Nro. Renovación', 'ttype': 'char'},
        {'code': 'pdf_resolucion', 'name': 'Pdf resolucion', 'ttype': 'binary'},
    ],
}


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    Campo = env['arsante.campo'].sudo()

    total = 0
    for xml_id, campos in PLAN.items():
        tipo = env.ref(xml_id, raise_if_not_found=False)
        if not tipo:
            _logger.warning("arsante: %s no encontrado, se omite", xml_id)
            continue

        existentes = set(Campo.with_context(active_test=False).search(
            [('tipo_registro_id', '=', tipo.id)]).mapped('code'))

        vals_list = []
        for i, datos in enumerate(campos):
            if datos['code'] in existentes:
                continue
            vals_list.append({
                'tipo_registro_id': tipo.id,
                'name': datos['name'],
                'code': datos['code'],
                'ttype': datos['ttype'],
                'comodel_name': datos.get('comodel_name', False),
                'seccion': 'izq',
                'sequence': 60 + i,
                'mostrar_en_formulario': True,
                'mostrar_en_lista': True,
                'mostrar_en_busqueda': True,
            })
        if not vals_list:
            continue

        Campo.create(vals_list)
        total += len(vals_list)
        _logger.info("arsante: agregados %d campos a %s (%s)",
                     len(vals_list), tipo.name,
                     ", ".join(v['code'] for v in vals_list))

    if total:
        env['arsante.registro'].clear_caches()
    _logger.info("arsante: barrido de vistas legacy completo, %d campos "
                 "agregados en total", total)
