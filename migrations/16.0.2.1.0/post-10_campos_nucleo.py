# -*- coding: utf-8 -*-
"""Expone los campos estándar en la configuración de cada tipo de registro.

Hasta ahora los campos comunes a todos los trámites (Cliente, Estado,
Facturado, No Cotizado…) estaban escritos directamente en la vista y no
aparecían en la lista de campos del tipo: el usuario los veía en el formulario
sin poder hacer nada con ellos, y la lista de configuración no explicaba lo que
realmente se muestra.

Este script crea su definición en los tipos existentes, todos visibles, de modo
que el formulario no cambia hasta que alguien decida ocultar alguno. Es
idempotente.
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    tipos = env['arsante.tipo_registro'].with_context(
        active_test=False).search([])
    if not tipos:
        return

    creados = tipos._asegurar_campos_nucleo()
    _logger.info("arsante: %d definiciones de campos estándar creadas en %d "
                 "tipos de registro", creados, len(tipos))
