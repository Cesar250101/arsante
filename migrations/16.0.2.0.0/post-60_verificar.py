# -*- coding: utf-8 -*-
"""Comprobaciones que abortan la migración si algo no cuadra.

Se ejecuta antes de que Odoo elimine las tablas legacy, y cualquier
``AssertionError`` revierte la transacción completa de ``-u arsante``: la base
queda exactamente como estaba. Es la red de seguridad principal, y es gratis.

Los valores esperados no están codificados: se comparan contra el snapshot que
tomó ``pre-10`` sobre la propia base, de modo que el script sirve igual en la
copia de pruebas y en producción.
"""

import logging

_logger = logging.getLogger(__name__)

ESQUEMA = 'arsante_backup'


def migrate(cr, version):
    if not version:
        return

    cr.execute("SELECT to_regclass('%s.control')" % ESQUEMA)
    if not cr.fetchone()[0]:
        _logger.warning("arsante: sin snapshot previo, se omite la verificación")
        return

    fallos = []
    resumen = []

    def comprobar(titulo, obtenido, esperado):
        ok = obtenido == esperado
        resumen.append("  %-46s %8s %s %s" % (
            titulo, obtenido, '==' if ok else '!=', esperado))
        if not ok:
            fallos.append("%s: se esperaban %s y hay %s"
                          % (titulo, esperado, obtenido))

    # Sólo cuentan las tablas de trámite, no all_record ni tipo_registro.
    cr.execute("""
        SELECT coalesce(sum(filas), 0), coalesce(sum(con_so), 0),
               coalesce(sum(facturados), 0)
          FROM %s.control
         WHERE tabla NOT IN ('arsante_all_record', 'arsante_tipo_registro',
                            'arsante_registro', 'arsante_campo',
                            'arsante_campo_opcion')
    """ % ESQUEMA)
    filas_ok, con_so_ok, facturados_ok = cr.fetchone()

    cr.execute("SELECT count(*) FROM arsante_registro")
    comprobar("1. registros migrados", cr.fetchone()[0], filas_ok)

    cr.execute("SELECT count(*) FROM arsante_registro WHERE sale_order_id IS NOT NULL")
    comprobar("2. con nota de venta", cr.fetchone()[0], con_so_ok)

    cr.execute("SELECT count(*) FROM arsante_registro WHERE facturado")
    comprobar("3. facturados", cr.fetchone()[0], facturados_ok)

    # 4. conteo por tabla de origen
    cr.execute("""
        SELECT c.tabla, c.filas,
               (SELECT count(*) FROM arsante_registro r
                 WHERE r.legacy_model = replace(c.tabla, 'arsante_', 'arsante.'))
          FROM %s.control c
         WHERE c.tabla NOT IN ('arsante_all_record', 'arsante_tipo_registro',
                              'arsante_registro', 'arsante_campo',
                              'arsante_campo_opcion')
         ORDER BY c.tabla
    """ % ESQUEMA)
    for tabla, esperado, obtenido in cr.fetchall():
        # legacy_model usa el primer guion bajo como punto: arsante.<resto>
        comprobar("4. %s" % tabla, obtenido, esperado)

    # 5. adjuntos
    cr.execute("SELECT count(*) FROM %s.ir_attachment_arsante "
               "WHERE res_field IS NOT NULL" % ESQUEMA)
    adjuntos_ok = cr.fetchone()[0]
    cr.execute("""SELECT count(*) FROM ir_attachment
                   WHERE res_model = 'arsante.registro'
                     AND res_field LIKE 'x!_arsante!_%' ESCAPE '!'""")
    comprobar("5. adjuntos reapuntados", cr.fetchone()[0], adjuntos_ok)

    cr.execute("""SELECT count(*) FROM ir_attachment
                   WHERE res_model LIKE 'arsante.%' AND res_model <> 'arsante.registro'""")
    comprobar("6. adjuntos huérfanos", cr.fetchone()[0], 0)

    # 7. integridad referencial con las notas de venta
    cr.execute("""
        SELECT count(*) FROM arsante_registro r
          LEFT JOIN sale_order s ON s.id = r.sale_order_id
         WHERE r.sale_order_id IS NOT NULL AND s.id IS NULL
    """)
    comprobar("7. notas de venta inexistentes", cr.fetchone()[0], 0)

    # 8. mapa de ids completo y sin duplicados
    cr.execute("SELECT count(*), count(DISTINCT (legacy_model, legacy_id)) "
               "FROM %s.mapa_ids" % ESQUEMA)
    total_mapa, distintos = cr.fetchone()
    comprobar("8. mapa de ids sin duplicados", total_mapa, distintos)
    comprobar("9. mapa de ids completo", total_mapa, filas_ok)

    # 10. ninguna columna dinámica puede ser NOT NULL: la comparten todos los
    # tipos y rompería los registros de los demás.
    cr.execute("""
        SELECT count(*) FROM information_schema.columns
         WHERE table_name = 'arsante_registro'
           AND column_name LIKE 'x!_arsante!_%' ESCAPE '!'
           AND is_nullable = 'NO'
    """)
    comprobar("10. columnas dinámicas obligatorias", cr.fetchone()[0], 0)

    # 11. cada definición de campo tiene su columna (o su adjunto)
    cr.execute("""
        SELECT count(*) FROM arsante_campo c
          JOIN ir_model_fields f ON f.id = c.ir_field_id
         WHERE f.ttype <> 'binary'
           AND NOT EXISTS (
               SELECT 1 FROM information_schema.columns col
                WHERE col.table_name = 'arsante_registro'
                  AND col.column_name = c.field_name)
    """)
    comprobar("11. campos sin columna física", cr.fetchone()[0], 0)

    cr.execute("SELECT count(*) FROM arsante_campo WHERE ir_field_id IS NULL")
    comprobar("12. campos sin ir.model.fields", cr.fetchone()[0], 0)

    _logger.info("arsante: verificación de la migración\n%s", "\n".join(resumen))

    if fallos:
        raise AssertionError(
            "La migración de arsante no cuadra; se revierte todo:\n - "
            + "\n - ".join(fallos))

    _logger.info("arsante: verificación superada (%d registros)", filas_ok)
