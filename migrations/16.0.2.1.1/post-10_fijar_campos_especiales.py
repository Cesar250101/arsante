# -*- coding: utf-8 -*-
"""Retira del catálogo configurable los campos con comportamiento especial.

``imagen``, ``sale_order_id``, ``oc_facturacion`` y ``comentario`` tienen
widget o atributos que el motor de inyección genérico no reproduce (imagen en
la esquina, visibilidad condicional según otro campo, pestaña propia). La
migración 16.0.2.1.0 los había dado de alta igual que cualquier otro campo
estándar, lo que los hacía aparecer DOS VECES en el formulario: una en su
posición fija de la vista y otra inyectados en la sección configurada.

Se elimina la definición (``arsante.campo``), no el dato: son campos Python
del modelo, sus columnas siguen existiendo tal cual y sus valores no se tocan.
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

CODIGOS_FIJOS = ('imagen', 'sale_order_id', 'oc_facturacion', 'comentario')


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    campos = env['arsante.campo'].with_context(active_test=False).search([
        ('es_nucleo', '=', True),
        ('code', 'in', list(CODIGOS_FIJOS)),
    ])
    if not campos:
        return

    campos.with_context(arsante_forzar_borrado=True).unlink()
    _logger.info("arsante: retiradas %d definiciones de campos con "
                 "comportamiento fijo (%s)",
                 len(campos), ", ".join(CODIGOS_FIJOS))
