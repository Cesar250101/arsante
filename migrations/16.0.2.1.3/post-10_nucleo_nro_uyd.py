# -*- coding: utf-8 -*-
"""Da de alta ``nro_uyd`` como campo estándar en todos los tipos.

A diferencia de ``marca_bijou`` (16.0.2.1.2), este código ya existía como
campo dinámico propio del tipo «UYD Alimentos» (``x_arsante_nro_uyd``, creado
por el catálogo de la migración 16.0.2.0.0 a partir de la columna legacy
``nro_uyd`` de ``arsante_uyd_alimentos``). Antes de darlo de alta como núcleo
hay que:

1. Copiar los valores de la columna dinámica a la nueva columna nativa.
2. Retirar la definición dinámica vieja (y con ella su columna
   ``x_arsante_nro_uyd``, vía ``unlink()``): si no se hiciera,
   ``_asegurar_campos_nucleo()`` encontraría el código «nro_uyd» ya usado en
   ese tipo y no crearía la definición de núcleo.

Después sí se reproduce el patrón de siempre: ``_asegurar_campos_nucleo()``
es idempotente y sólo añade lo que falte en cada tipo.
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    cr.execute("""SELECT column_name FROM information_schema.columns
                   WHERE table_name = 'arsante_registro'
                     AND column_name = 'x_arsante_nro_uyd'""")
    if cr.fetchone():
        cr.execute("""UPDATE arsante_registro SET nro_uyd = x_arsante_nro_uyd
                       WHERE x_arsante_nro_uyd IS NOT NULL""")
        _logger.info("arsante: copiados %d valores de x_arsante_nro_uyd a "
                     "nro_uyd", cr.rowcount)

    viejo = env['arsante.campo'].with_context(active_test=False).search([
        ('code', '=', 'nro_uyd'), ('es_nucleo', '=', False),
    ])
    if viejo:
        viejo.with_context(arsante_forzar_borrado=True).unlink()
        _logger.info("arsante: retirada la definición dinámica antigua de "
                     "nro_uyd (%d tipo/s)", len(viejo))

    tipos = env['arsante.tipo_registro'].with_context(
        active_test=False).search([])
    creados = tipos._asegurar_campos_nucleo()
    _logger.info("arsante: %d definiciones nuevas al añadir nro_uyd "
                 "(sólo se crea lo que faltaba en %d tipos)",
                 creados, len(tipos))
