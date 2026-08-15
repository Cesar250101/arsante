# -*- coding: utf-8 -*-
"""Reapunta los adjuntos de los trámites al modelo genérico.

Los campos Binary de Odoo con ``attachment=True`` no tienen columna: su
contenido vive en ``ir_attachment``, identificado por ``res_model`` +
``res_field`` + ``res_id``. Al migrar los registros hay que reescribir esos tres
datos o los 1.101 PDF de resolución quedarían huérfanos y no se podrían
descargar desde el formulario.

Sólo se tocan las columnas de enlace: el fichero físico del filestore no se
mueve ni se vuelve a escribir.
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

ESQUEMA = 'arsante_backup'


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    # code -> field_name de los campos binary del catálogo.
    binarios = {}
    for campo in env['arsante.campo'].search([('ttype', '=', 'binary')]):
        binarios[campo.code.split('__')[0]] = campo.field_name
    if not binarios:
        _logger.info("arsante: no hay campos binary en el catálogo")
        return

    total = 0
    for code, field_name in sorted(binarios.items()):
        cr.execute("""
            UPDATE ir_attachment a
               SET res_model = 'arsante.registro',
                   res_field = %s,
                   res_id    = m.nuevo_id
              FROM {esquema}.mapa_ids m
             WHERE a.res_model = m.legacy_model
               AND a.res_id    = m.legacy_id
               AND a.res_field = %s
        """.format(esquema=ESQUEMA), (field_name, code))
        _logger.info("arsante: %d adjuntos de %s -> %s",
                     cr.rowcount, code, field_name)
        total += cr.rowcount

    # Nada debe quedar apuntando a un modelo de trámite que va a desaparecer.
    cr.execute("""
        SELECT res_model, res_field, count(*)
          FROM ir_attachment
         WHERE res_model LIKE 'arsante.%%' AND res_model <> 'arsante.registro'
         GROUP BY 1, 2
    """)
    huerfanos = cr.fetchall()
    if huerfanos:
        for modelo, campo, n in huerfanos:
            _logger.warning("arsante: quedan %d adjuntos en %s.%s sin migrar",
                            n, modelo, campo)
        cr.execute("""
            CREATE TABLE IF NOT EXISTS arsante_backup.informe (
                momento text, detalle text, ts timestamp DEFAULT now())
        """)
        for modelo, campo, n in huerfanos:
            cr.execute("INSERT INTO arsante_backup.informe (momento, detalle) "
                       "VALUES ('adjuntos', %s)",
                       ("%d adjuntos siguen en %s.%s" % (n, modelo, campo),))

    _logger.info("arsante: %d adjuntos reapuntados a arsante.registro", total)
