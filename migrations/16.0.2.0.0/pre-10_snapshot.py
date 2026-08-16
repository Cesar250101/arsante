# -*- coding: utf-8 -*-
"""Copia de seguridad de las tablas de trámite ANTES de tocar nada.

Se ejecuta en la fase ``pre-``, cuando el módulo todavía no se ha importado:
aquí sólo existe ``cr``, no el ORM de arsante.

Por qué es imprescindible: al eliminar los 22 modelos del código, ``_process_end``
borra sus ``ir.model`` y con ellos los menús, acciones y vistas asociados. Esta
copia es la única forma de recuperar el estado dentro de la misma transacción si
algo sale mal después de ese punto.

Comprobado en la práctica sobre una copia de producción: Odoo elimina los
``ir.model`` pero **no** hace ``DROP TABLE`` de los modelos ``state='base'``, así
que las tablas originales sobreviven con sus datos. Es una red de seguridad
extra, no un motivo para prescindir de esta copia: los ``ir.model.data``,
menús y acciones sí desaparecen, y sin este respaldo no habría forma de
reconstruir el estado previo.

``CREATE TABLE ... AS TABLE`` copia los datos pero NO las claves, índices ni
valores por defecto, así que además se guarda el DDL necesario para poder
reconstruirlas en un rollback manual.
"""

import logging

_logger = logging.getLogger(__name__)

ESQUEMA = 'arsante_backup'


def migrate(cr, version):
    if not version:
        return  # instalación nueva: no hay nada que respaldar

    cr.execute("CREATE SCHEMA IF NOT EXISTS %s" % ESQUEMA)

    tablas = _tablas_arsante(cr)
    if not tablas:
        _logger.warning("arsante: no se encontraron tablas que respaldar")
        return

    cr.execute("""
        CREATE TABLE IF NOT EXISTS %s.control (
            tabla text, filas bigint, con_so bigint, facturados bigint,
            ts timestamp DEFAULT now())
    """ % ESQUEMA)
    cr.execute("DELETE FROM %s.control" % ESQUEMA)

    cr.execute("""
        CREATE TABLE IF NOT EXISTS %s.ddl (
            tabla text, tipo text, definicion text)
    """ % ESQUEMA)
    cr.execute("DELETE FROM %s.ddl" % ESQUEMA)

    total = 0
    for tabla in tablas:
        cr.execute('DROP TABLE IF EXISTS %s."%s"' % (ESQUEMA, tabla))
        cr.execute('CREATE TABLE %s."%s" AS TABLE public."%s"'
                   % (ESQUEMA, tabla, tabla))

        filas = _contar(cr, tabla, '*')
        con_so = _contar(cr, tabla, 'sale_order_id')
        facturados = _contar_facturados(cr, tabla)
        cr.execute(
            "INSERT INTO %s.control (tabla, filas, con_so, facturados) "
            "VALUES (%%s, %%s, %%s, %%s)" % ESQUEMA,
            (tabla, filas, con_so, facturados))
        total += filas

        _guardar_ddl(cr, tabla)

    # Los adjuntos no viven en las tablas de trámite: hay que respaldarlos
    # aparte porque la migración les cambia res_model/res_field/res_id.
    cr.execute("DROP TABLE IF EXISTS %s.ir_attachment_arsante" % ESQUEMA)
    cr.execute("""
        CREATE TABLE %s.ir_attachment_arsante AS
        SELECT id, res_model, res_field, res_id
          FROM ir_attachment
         WHERE res_model LIKE 'arsante.%%'
    """ % ESQUEMA)
    cr.execute("SELECT count(*) FROM %s.ir_attachment_arsante" % ESQUEMA)
    adjuntos = cr.fetchone()[0]

    # Mapa legacy -> nuevo, que rellenará post-40. Se crea aquí para que exista
    # aunque la migración de datos falle a mitad.
    #
    # NUNCA se borra si ya existe (a diferencia de las demás tablas de este
    # esquema, que sí se recrean en cada intento): post-40 es idempotente y
    # OMITE los registros que ya estén migrados de un intento anterior, así
    # que no vuelve a insertar su fila en mapa_ids. Si aquí se vaciara el mapa
    # en cada corrida, esos registros ya migrados quedarían sin mapeo y
    # post-60 fallaría con "mapa de ids completo" aunque los datos estén bien.
    cr.execute("""
        CREATE TABLE IF NOT EXISTS %s.mapa_ids (
            legacy_model text, legacy_id integer, nuevo_id integer)
    """ % ESQUEMA)

    _logger.info("arsante: respaldadas %d tablas, %d registros y %d adjuntos "
                 "en el esquema %s", len(tablas), total, adjuntos, ESQUEMA)


def _tablas_arsante(cr):
    """Tablas de trámite: las que tienen tipo_registro_id, más all_record."""
    cr.execute("""
        SELECT DISTINCT c.table_name
          FROM information_schema.columns c
         WHERE c.table_schema = 'public'
           AND c.table_name LIKE 'arsante!_%' ESCAPE '!'
           AND c.table_name NOT LIKE '%!_wizard' ESCAPE '!'
           AND c.column_name = 'tipo_registro_id'
         ORDER BY 1
    """)
    tablas = [r[0] for r in cr.fetchall()]
    for extra in ('arsante_all_record', 'arsante_tipo_registro'):
        if extra not in tablas and _existe(cr, extra):
            tablas.append(extra)
    return tablas


def _existe(cr, tabla):
    cr.execute("SELECT to_regclass(%s)", ('public.' + tabla,))
    return bool(cr.fetchone()[0])


def _columnas(cr, tabla):
    cr.execute("""SELECT column_name FROM information_schema.columns
                   WHERE table_schema='public' AND table_name=%s""", (tabla,))
    return {r[0] for r in cr.fetchall()}


def _contar(cr, tabla, columna):
    """Cuenta filas o valores no nulos.

    Se comprueba antes que la columna exista en vez de capturar la excepción:
    un error de SQL aborta la transacción en PostgreSQL, y hacer rollback aquí
    se llevaría por delante el esquema de respaldo que acabamos de crear.
    """
    if columna != '*' and columna not in _columnas(cr, tabla):
        return 0
    cr.execute('SELECT count(%s) FROM public."%s"' % (
        '*' if columna == '*' else '"%s"' % columna, tabla))
    return cr.fetchone()[0]


def _contar_facturados(cr, tabla):
    if 'facturado' not in _columnas(cr, tabla):
        return 0
    cr.execute('SELECT count(*) FROM public."%s" WHERE facturado' % tabla)
    return cr.fetchone()[0]


def _guardar_ddl(cr, tabla):
    """Guarda índices y restricciones para poder rehacerlos en un rollback."""
    cr.execute("SELECT indexdef FROM pg_indexes "
               "WHERE schemaname='public' AND tablename=%s", (tabla,))
    for (definicion,) in cr.fetchall():
        cr.execute("INSERT INTO %s.ddl VALUES (%%s,'index',%%s)" % ESQUEMA,
                   (tabla, definicion))

    cr.execute("""
        SELECT conname, pg_get_constraintdef(oid)
          FROM pg_constraint
         WHERE conrelid = %s::regclass
    """, ('public."%s"' % tabla,))
    for nombre, definicion in cr.fetchall():
        cr.execute("INSERT INTO %s.ddl VALUES (%%s,'constraint',%%s)" % ESQUEMA,
                   (tabla, 'ALTER TABLE public."%s" ADD CONSTRAINT "%s" %s'
                    % (tabla, nombre, definicion)))
