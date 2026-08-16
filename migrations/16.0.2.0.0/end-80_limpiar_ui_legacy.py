# -*- coding: utf-8 -*-
"""Elimina menús, acciones y vistas de los modelos de trámite ya retirados.

Red de seguridad, normalmente sin trabajo que hacer.

En el camino habitual ``_process_end`` ya se encarga: al desaparecer los modelos
y sus ficheros XML, Odoo elimina sus ``ir.model``, menús, acciones y vistas, y
este script no encuentra nada obsoleto. Sirve para los casos en que sí queda
algo suelto: menús creados a mano desde la interfaz (sin external ID, que
``_process_end`` no puede reconocer) o restos de instalaciones anteriores. Sin
esta limpieza el usuario vería dos entradas por trámite, la nueva y una vieja
que revienta al pulsarla.

Toca sólo objetos de **interfaz**. Deliberadamente NO toca ``ir.model`` ni las
tablas: Odoo conserva las tablas de los modelos ``state='base'`` aunque borre su
``ir.model``, y esos datos originales son la mejor red de seguridad hasta que la
migración lleve tiempo validada.

Se ejecuta después de ``end-70``, que es quien crea los menús nuevos.
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    obsoletos = _modelos_obsoletos(env)
    if not obsoletos:
        _logger.info("arsante: no hay modelos obsoletos que limpiar")
        return

    _logger.info("arsante: limpiando la interfaz de %d modelos retirados: %s",
                 len(obsoletos), ", ".join(sorted(obsoletos)))

    borrados = {
        'menús': _borrar_menus(env, obsoletos),
        'acciones de ventana': _borrar(env, 'ir.actions.act_window', 'res_model', obsoletos),
        'acciones de servidor': _borrar_servidor(env, obsoletos),
        'vistas': _borrar(env, 'ir.ui.view', 'model', obsoletos),
        'permisos': _borrar_acl(env, obsoletos),
    }
    _logger.info("arsante: eliminados %s",
                 ", ".join("%d %s" % (n, k) for k, n in borrados.items() if n))

    _avisar_pendiente(cr, obsoletos)


def _modelos_obsoletos(env):
    """Modelos arsante que están en ir_model pero ya no tienen clase Python."""
    env.cr.execute("SELECT model FROM ir_model WHERE model LIKE 'arsante.%'")
    return {m for (m,) in env.cr.fetchall() if m not in env.registry}


def _borrar_menus(env, obsoletos):
    """Menús cuya acción apunta a un modelo retirado."""
    Menu = env['ir.ui.menu'].sudo().with_context(active_test=False)
    a_borrar = Menu.browse()
    for menu in Menu.search([('action', '!=', False)]):
        try:
            accion = menu.action
        except Exception:
            continue
        if accion and getattr(accion, 'res_model', None) in obsoletos:
            a_borrar |= menu
    n = len(a_borrar)
    if a_borrar:
        a_borrar.unlink()
    return n


def _borrar(env, modelo, campo, obsoletos):
    """Borra registros de ``modelo`` cuyo ``campo`` apunte a un modelo retirado.

    ir.ui.view usa el campo 'model'; ir.actions.act_window usa 'res_model' —
    de ahí el parámetro en vez de asumir el mismo nombre para ambos.
    """
    registros = env[modelo].sudo().with_context(active_test=False).search(
        [(campo, 'in', list(obsoletos))])
    n = len(registros)
    if registros:
        registros.unlink()
    return n


def _borrar_servidor(env, obsoletos):
    Servidor = env['ir.actions.server'].sudo()
    acciones = Servidor.search([('model_id.model', 'in', list(obsoletos))])
    n = len(acciones)
    if acciones:
        acciones.unlink()
    return n


def _borrar_acl(env, obsoletos):
    acl = env['ir.model.access'].sudo().search(
        [('model_id.model', 'in', list(obsoletos))])
    n = len(acl)
    if acl:
        acl.unlink()
    return n


def _avisar_pendiente(cr, obsoletos):
    """Deja constancia de lo que queda por limpiar más adelante."""
    cr.execute("""
        CREATE TABLE IF NOT EXISTS arsante_backup.informe (
            momento text, detalle text, ts timestamp DEFAULT now())
    """)
    detalle = (
        "Se conservan las tablas y los ir.model de %d modelos retirados (%s). "
        "Contienen los datos originales y sirven de respaldo adicional junto "
        "al esquema arsante_backup. Elimínelos cuando la migración lleve "
        "tiempo validada; hasta entonces Odoo sólo registrará un aviso "
        "'declared but cannot be loaded' por cada uno al arrancar."
        % (len(obsoletos), ", ".join(sorted(obsoletos)[:5]) + "…"))
    cr.execute("INSERT INTO arsante_backup.informe (momento, detalle) "
               "VALUES ('limpieza', %s)", (detalle,))
    _logger.warning("arsante: %s", detalle)
