# -*- coding: utf-8 -*-
"""Desactiva el cron que alimentaba ``arsante.all_record``.

Ese cron copiaba cada 10 minutos los registros de los 22 modelos a una tabla
consolidada. Con un único modelo genérico no hay nada que consolidar, y si
siguiera activo durante la migración competiría por las mismas filas.

Se desactiva en vez de borrarlo: el registro desaparece solo cuando se elimine
``data/cron.xml`` del manifest (fase de limpieza), y así la operación es
reversible si hubiera que volver atrás.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    # ir.cron hereda de ir.actions.server (_inherits), así que el modelo sobre
    # el que actúa vive en ir_act_server, no en ir_cron.
    cr.execute("""
        UPDATE ir_cron SET active = false
         WHERE id IN (
            SELECT c.id
              FROM ir_cron c
              JOIN ir_act_server s ON s.id = c.ir_actions_server_id
              JOIN ir_model m ON m.id = s.model_id
             WHERE m.model = 'arsante.all_record'
         )
         RETURNING id
    """)
    filas = cr.fetchall()
    if filas:
        _logger.info("arsante: desactivados %d cron de all_record", len(filas))
    else:
        _logger.info("arsante: no había cron de all_record activo")
