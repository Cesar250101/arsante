# -*- coding: utf-8 -*-
"""Informe final de la migración. No falla nunca.

Se ejecuta en la fase ``end-``, la última, y sólo resume lo que quedó anotado en
``arsante_backup.informe`` durante el proceso: colisiones de código, filas con
el tipo de registro cruzado y adjuntos sin migrar. Son cosas que requieren
criterio humano, no motivo para abortar.

Además regenera los menús de los tipos de registro, para que los que no tenían
menú propio (8 de los 22 modelos no eran navegables) pasen a tenerlo.
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

ESQUEMA = 'arsante_backup'


def migrate(cr, version):
    if not version:
        return

    _regenerar_menus(cr)
    _resumen(cr)


def _regenerar_menus(cr):
    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        tipos = env['arsante.tipo_registro'].search(
            [('active', 'in', (True, False))])
        tipos._sync_menu()
        _logger.info("arsante: menús regenerados para %d tipos de registro",
                     len(tipos))
    except Exception:
        _logger.exception("arsante: no se pudieron regenerar los menús")


def _resumen(cr):
    cr.execute("SELECT to_regclass('%s.informe')" % ESQUEMA)
    if not cr.fetchone()[0]:
        _logger.info("arsante: migración sin incidencias que revisar")
        return

    cr.execute("SELECT momento, detalle FROM %s.informe ORDER BY momento, ts"
               % ESQUEMA)
    filas = cr.fetchall()
    if not filas:
        _logger.info("arsante: migración sin incidencias que revisar")
        return

    lineas = ["", "=" * 72,
              "ARSANTE - puntos a revisar manualmente tras la migración",
              "=" * 72]
    momento_actual = None
    for momento, detalle in filas:
        if momento != momento_actual:
            lineas.append("")
            lineas.append("[%s]" % momento)
            momento_actual = momento
        lineas.append("  - %s" % detalle)
    lineas.append("")
    lineas.append("Copia de seguridad de las tablas originales: esquema '%s'."
                  % ESQUEMA)
    lineas.append("=" * 72)
    _logger.warning("\n".join(lineas))
