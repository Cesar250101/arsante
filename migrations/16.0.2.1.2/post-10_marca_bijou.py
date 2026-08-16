# -*- coding: utf-8 -*-
"""Da de alta ``marca_bijou`` como campo estándar en los tipos existentes.

Reproduce el patrón de "marca" que tenían cda_cosmetico_dm.py,
rev_antecedentes_dm.py y otros modelos legacy: Selection (No Aplica/Todo
Moda/Isadora) + botón que abre la carpeta de colillas de pago en SharePoint.

Se llama a ``_asegurar_campos_nucleo()``, la misma función que ya crea el
resto de campos estándar: es idempotente, así que sólo añade lo que falte.
Nace visible en los 20 tipos por defecto, igual que el resto de campos
estándar (Estado, Facturado…); el usuario puede ocultarlo por tipo desde la
configuración donde no aplique.
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
    _logger.info("arsante: %d definiciones nuevas al añadir marca_bijou "
                 "(sólo se crea lo que faltaba en %d tipos)",
                 creados, len(tipos))
