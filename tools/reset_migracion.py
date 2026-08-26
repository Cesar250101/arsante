#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deshace la migración para poder repetirla, SOLO en bases de pruebas.

Restaura las tablas de trámite desde el esquema ``arsante_backup``, borra todo
lo que creó la migración (registros, definiciones de campo, columnas dinámicas,
menús y acciones generados) y baja la versión instalada del módulo para que los
scripts vuelvan a ejecutarse.

Permite repetir la migración en un minuto en vez de restaurar un dump de 4 GB,
que es lo que hace falta para comprobar que el proceso es determinista.

Se niega a tocar la base de producción.

Uso:
    python tools/reset_migracion.py --db clicksale_test
"""

import argparse
import os
import sys

try:
    import psycopg2
except ImportError:
    sys.exit("psycopg2 no disponible. Ejecute con el Python de Odoo.")

# Salvaguarda: nombres que nunca se pueden resetear.
PROHIBIDAS = {'clicksale', 'odoo', 'postgres', 'template0', 'template1'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', default='5432')
    parser.add_argument('--user', default='odoo')
    parser.add_argument('--password', default=os.environ.get('PGPASSWORD', ''))
    parser.add_argument('--si-estoy-seguro', action='store_true',
                        help='Necesario para bases que no acaben en _test')
    args = parser.parse_args()

    if args.db in PROHIBIDAS:
        sys.exit("NEGADO: '%s' es una base protegida." % args.db)
    if not args.db.endswith('_test') and not args.si_estoy_seguro:
        sys.exit("NEGADO: '%s' no acaba en _test. Use --si-estoy-seguro si "
                 "de verdad es una base desechable." % args.db)

    conexion = psycopg2.connect(dbname=args.db, host=args.host, port=args.port,
                                user=args.user, password=args.password)
    conexion.autocommit = False
    try:
        with conexion.cursor() as cur:
            resetear(cur)
        conexion.commit()
        print("\nReset completado. Ejecute de nuevo:")
        print('  odoo-bin -d %s -u arsante --stop-after-init' % args.db)
    finally:
        conexion.close()


def resetear(cur):
    cur.execute("SELECT to_regclass('arsante_backup.control')")
    if not cur.fetchone()[0]:
        sys.exit("No hay copia en arsante_backup: nada que restaurar. "
                 "¿Se llegó a ejecutar la migración?")

    # 1. restaurar las tablas de trámite desde la copia.
    # arsante_tipo_registro se deja fuera: es el catálogo maestro al que apuntan
    # todas las demás por clave ajena, y vaciarlo rompería esas referencias. Sus
    # menu_id/action_id se limpian aparte, más abajo. Las tablas del sistema
    # nuevo también se vacían aparte.
    sin_restaurar = ('arsante_tipo_registro', 'arsante_registro',
                     'arsante_campo', 'arsante_campo_opcion')
    cur.execute("""
        SELECT table_name FROM information_schema.tables
         WHERE table_schema = 'arsante_backup'
           AND table_name LIKE 'arsante!_%%' ESCAPE '!'
           AND table_name NOT IN %s
    """, (sin_restaurar,))
    tablas = [r[0] for r in cur.fetchall()]
    for tabla in tablas:
        cur.execute("SELECT to_regclass('public.%s')" % tabla)
        if not cur.fetchone()[0]:
            continue
        cur.execute('DELETE FROM public."%s"' % tabla)
        cur.execute('INSERT INTO public."%s" SELECT * FROM arsante_backup."%s"'
                    % (tabla, tabla))
        print("  restaurada  %-45s %d filas" % (tabla, cur.rowcount))

    # 2. restaurar los adjuntos a su modelo y campo originales
    cur.execute("""
        UPDATE ir_attachment a
           SET res_model = b.res_model, res_field = b.res_field, res_id = b.res_id
          FROM arsante_backup.ir_attachment_arsante b
         WHERE a.id = b.id
    """)
    print("  adjuntos restaurados: %d" % cur.rowcount)

    # 3. borrar los registros migrados
    cur.execute("SELECT to_regclass('public.arsante_registro')")
    if cur.fetchone()[0]:
        cur.execute("DELETE FROM arsante_registro")
        print("  registros genéricos borrados: %d" % cur.rowcount)

    # 4. borrar las columnas dinámicas y sus definiciones
    cur.execute("""
        SELECT f.id, f.name FROM ir_model_fields f
         WHERE f.model = 'arsante.registro' AND f.state = 'manual'
           AND f.name LIKE 'x!_arsante!_%' ESCAPE '!'
    """)
    campos = cur.fetchall()
    for _id, nombre in campos:
        cur.execute('ALTER TABLE arsante_registro DROP COLUMN IF EXISTS "%s" CASCADE'
                    % nombre)
    if campos:
        cur.execute("DELETE FROM ir_model_fields_selection WHERE field_id IN %s",
                    (tuple(i for i, _n in campos),))
        cur.execute("DELETE FROM ir_model_fields WHERE id IN %s",
                    (tuple(i for i, _n in campos),))
    print("  columnas dinámicas eliminadas: %d" % len(campos))

    for tabla in ('arsante_campo_opcion', 'arsante_campo'):
        cur.execute("SELECT to_regclass('public.%s')" % tabla)
        if cur.fetchone()[0]:
            cur.execute('DELETE FROM %s' % tabla)

    # 5. menús y acciones generados por _sync_menu
    cur.execute("""
        DELETE FROM ir_ui_menu WHERE id IN (
            SELECT menu_id FROM arsante_tipo_registro WHERE menu_id IS NOT NULL)
    """)
    cur.execute("""
        DELETE FROM ir_act_window WHERE id IN (
            SELECT action_id FROM arsante_tipo_registro WHERE action_id IS NOT NULL)
    """)
    cur.execute("UPDATE arsante_tipo_registro SET menu_id = NULL, action_id = NULL")

    # 6. reactivar el cron y limpiar el informe
    # ir.cron hereda de ir.actions.server: el modelo vive en ir_act_server.
    cur.execute("""
        UPDATE ir_cron SET active = true
         WHERE id IN (
            SELECT c.id FROM ir_cron c
              JOIN ir_act_server s ON s.id = c.ir_actions_server_id
              JOIN ir_model m ON m.id = s.model_id
             WHERE m.model = 'arsante.all_record')
    """)
    cur.execute("DROP TABLE IF EXISTS arsante_backup.informe")
    cur.execute("DELETE FROM arsante_backup.mapa_ids")

    # 7. bajar la version instalada para que los scripts vuelvan a correr
    cur.execute("UPDATE ir_module_module SET latest_version = '16.0.0.1' "
                "WHERE name = 'arsante'")
    print("  version del modulo -> 16.0.0.1 (la migracion volvera a ejecutarse)")


if __name__ == '__main__':
    main()
