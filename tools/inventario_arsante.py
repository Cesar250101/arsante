#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inventario del módulo arsante: esquema real de las tablas de trámite.

SOLO LECTURA. No modifica la base de datos ni el módulo.

Cruza tres fuentes:
  1. ``information_schema`` (tipo SQL real de cada columna)
  2. Conteos reales de filas y valores no nulos
  3. El AST de los ``models/*.py`` (ttype declarado, comodel, opciones de Selection)

Genera el CSV canónico que consumen ``migrations/16.0.2.0.0/post-30_catalogo_campos.py``
y las verificaciones de ``post-60_verificar.py``.

Uso:
    python tools/inventario_arsante.py --db clicksale
    python tools/inventario_arsante.py --db clicksale_test --salida /tmp/inv.csv
"""

import argparse
import ast
import csv
import os
import sys
from collections import OrderedDict

try:
    import psycopg2
except ImportError:
    sys.exit("psycopg2 no disponible. Ejecute con el Python de Odoo.")


# Columnas que pasan a ser campos "duros" de arsante.registro, más las técnicas
# de Odoo. Nunca generan un arsante.campo.
NUCLEO = {
    'id', 'create_uid', 'create_date', 'write_uid', 'write_date',
    'name', 'date', 'partner_id', 'product_id', 'tipo_registro_id',
    'estado', 'documentacion', 'facturado', 'no_cotizado', 'espera_resolucion',
    'requiere_renovacion', 'fecha_renovacion', 'alerta_renovacion',
    'nro_resolucion', 'comentario', 'sale_order_id', 'active', 'importado',
}

# Un modelo es "de trámite" si declara tipo_registro_id. Se comprueba sobre el
# AST en vez de mantener una lista, para que el inventario no se desactualice
# al añadir o quitar modelos.
MARCADOR_TRAMITE = 'tipo_registro_id'

# Excepciones: declaran tipo_registro_id pero no son trámites.
NO_TRAMITE = {
    'arsante.tipo_registro', 'arsante.all_record',
}

# data_type de PostgreSQL -> ttype de Odoo. Las columnas *_id se resuelven
# aparte contra el comodel declarado en el .py.
MAPA_PG = {
    'boolean': 'boolean',
    'date': 'date',
    'timestamp without time zone': 'datetime',
    'numeric': 'float',
    'double precision': 'float',
    'text': 'text',
    'character varying': 'char',
    'integer': 'integer',
    'bigint': 'integer',
}


def modelos_desde_python(dir_models):
    """Parsea models/*.py y devuelve {tabla_sql: {columna: info_declarada}}.

    info_declarada = {'ttype', 'comodel', 'selection', 'string'}
    Se usa el AST y no import, para no requerir un entorno Odoo cargado.
    """
    resultado = {}
    for fichero in sorted(os.listdir(dir_models)):
        if not fichero.endswith('.py') or fichero == '__init__.py':
            continue
        ruta = os.path.join(dir_models, fichero)
        with open(ruta, encoding='utf-8') as fh:
            try:
                arbol = ast.parse(fh.read(), filename=ruta)
            except SyntaxError as exc:
                print("  ! %s no parsea: %s" % (fichero, exc), file=sys.stderr)
                continue

        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.ClassDef):
                continue
            nombre_modelo = _leer_name(nodo)
            if not nombre_modelo or nombre_modelo in NO_TRAMITE:
                continue
            campos = _leer_campos(nodo)
            if MARCADOR_TRAMITE in campos:
                tabla = nombre_modelo.replace('.', '_')
                resultado[tabla] = {'_modelo': nombre_modelo,
                                    '_fichero': fichero,
                                    'campos': campos}
    return resultado


def _leer_name(clase):
    """Devuelve el valor de _name de una ClassDef, o None si no lo declara."""
    for cuerpo in clase.body:
        if not isinstance(cuerpo, ast.Assign):
            continue
        for destino in cuerpo.targets:
            if isinstance(destino, ast.Name) and destino.id == '_name':
                if isinstance(cuerpo.value, ast.Constant):
                    return cuerpo.value.value
    return None


def _leer_campos(clase):
    """Extrae {nombre_campo: {ttype, comodel, selection}} de una ClassDef."""
    campos = {}
    for cuerpo in clase.body:
        if not isinstance(cuerpo, ast.Assign) or not isinstance(cuerpo.value, ast.Call):
            continue
        llamada = cuerpo.value
        # fields.Char(...) -> Attribute(value=Name('fields'), attr='Char')
        if not isinstance(llamada.func, ast.Attribute):
            continue
        if not (isinstance(llamada.func.value, ast.Name)
                and llamada.func.value.id == 'fields'):
            continue
        ttype = llamada.func.attr.lower()
        for destino in cuerpo.targets:
            if not isinstance(destino, ast.Name):
                continue
            campos[destino.id] = {
                'ttype': ttype,
                'comodel': _leer_comodel(llamada),
                'selection': _leer_selection(llamada),
                'string': _leer_kwarg_str(llamada, 'string'),
                'related': bool(_leer_kwarg_str(llamada, 'related')),
                'compute': bool(_leer_kwarg_str(llamada, 'compute')),
            }
    return campos


def _leer_comodel(llamada):
    """comodel_name='res.partner' o primer posicional en Many2one('res.partner')."""
    valor = _leer_kwarg_str(llamada, 'comodel_name')
    if valor:
        return valor
    if llamada.args and isinstance(llamada.args[0], ast.Constant):
        if isinstance(llamada.args[0].value, str):
            return llamada.args[0].value
    return None


def _leer_kwarg_str(llamada, nombre):
    for kw in llamada.keywords:
        if kw.arg == nombre and isinstance(kw.value, ast.Constant):
            return kw.value.value
    return None


def _leer_selection(llamada):
    """Devuelve [(code, label), ...] de un fields.Selection, o []."""
    nodo = None
    for kw in llamada.keywords:
        if kw.arg == 'selection':
            nodo = kw.value
    if nodo is None and llamada.args and isinstance(llamada.args[0], ast.List):
        nodo = llamada.args[0]
    if not isinstance(nodo, ast.List):
        return []
    opciones = []
    for elemento in nodo.elts:
        if isinstance(elemento, ast.Tuple) and len(elemento.elts) == 2:
            par = elemento.elts
            if all(isinstance(x, ast.Constant) for x in par):
                opciones.append((par[0].value, par[1].value))
    return opciones


def inventariar(cur, tablas_py):
    """Cruza el esquema SQL con lo declarado en Python. Devuelve filas del CSV."""
    filas = []
    cur.execute("""
        SELECT table_name FROM information_schema.tables
         WHERE table_schema = 'public' AND table_name LIKE 'arsante!_%%' ESCAPE '!'
         ORDER BY table_name
    """)
    tablas_sql = [r[0] for r in cur.fetchall()]

    for tabla in tablas_sql:
        if tabla not in tablas_py:
            continue  # wizards, _correo, no-trámites: fuera del inventario
        info_py = tablas_py[tabla]

        cur.execute('SELECT count(*) FROM public."%s"' % tabla)
        total_filas = cur.fetchone()[0]

        cur.execute("""
            SELECT column_name, data_type
              FROM information_schema.columns
             WHERE table_schema = 'public' AND table_name = %s
             ORDER BY ordinal_position
        """, (tabla,))
        columnas = cur.fetchall()

        for columna, tipo_pg in columnas:
            # count(col) ignora los NULL: da directamente los valores poblados.
            cur.execute('SELECT count("%s") FROM public."%s"' % (columna, tabla))
            no_nulos = cur.fetchone()[0]
            cur.execute('SELECT count(DISTINCT "%s") FROM public."%s"' % (columna, tabla))
            distintos = cur.fetchone()[0]

            decl = info_py['campos'].get(columna, {})
            ttype = _inferir_ttype(columna, tipo_pg, decl)

            valores_bd = ''
            if ttype == 'selection' and no_nulos:
                cur.execute(
                    'SELECT DISTINCT "%s" FROM public."%s" WHERE "%s" IS NOT NULL'
                    % (columna, tabla, columna))
                valores_bd = '|'.join(sorted(str(r[0]) for r in cur.fetchall()))

            filas.append(OrderedDict([
                ('tabla', tabla),
                ('modelo', info_py['_modelo']),
                ('fichero', info_py['_fichero']),
                ('columna', columna),
                ('nucleo', 'si' if columna in NUCLEO else 'no'),
                ('tipo_pg', tipo_pg),
                ('ttype_declarado', decl.get('ttype', '')),
                ('ttype_inferido', ttype),
                ('comodel', decl.get('comodel') or ''),
                ('etiqueta', decl.get('string') or ''),
                ('filas_tabla', total_filas),
                ('no_nulos', no_nulos),
                ('distintos', distintos),
                ('selection_py', '|'.join(c for c, _ in decl.get('selection') or [])),
                ('selection_bd', valores_bd),
                ('migrar', _decidir_migrar(columna, no_nulos, decl)),
            ]))
    return filas


def _inferir_ttype(columna, tipo_pg, decl):
    """El .py manda; information_schema desempata. Los *_id son many2one."""
    declarado = decl.get('ttype')
    if declarado in ('char', 'text', 'integer', 'float', 'monetary', 'date',
                     'datetime', 'boolean', 'binary', 'selection', 'many2one'):
        return 'float' if declarado == 'monetary' else declarado
    if tipo_pg == 'integer' and columna.endswith('_id'):
        return 'many2one'
    return MAPA_PG.get(tipo_pg, 'char')


def _decidir_migrar(columna, no_nulos, decl):
    """Sólo se convierte en arsante.campo lo que es específico y tiene datos."""
    if columna in NUCLEO:
        return 'no:nucleo'
    if decl.get('related') or decl.get('compute'):
        return 'no:calculado'
    if not no_nulos:
        return 'no:vacia'
    return 'si'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='clicksale')
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', default='5432')
    parser.add_argument('--user', default='odoo')
    parser.add_argument('--password', default=os.environ.get('PGPASSWORD', ''))
    parser.add_argument('--modelos', default=None,
                        help='Ruta a models/ (por defecto, relativa a este script)')
    parser.add_argument('--salida', default=None)
    args = parser.parse_args()

    dir_models = args.modelos or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'models')
    salida = args.salida or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'inventario_arsante.csv')

    print("Parseando %s ..." % os.path.normpath(dir_models))
    tablas_py = modelos_desde_python(dir_models)
    print("  %d modelos de trámite detectados" % len(tablas_py))

    conexion = psycopg2.connect(dbname=args.db, host=args.host, port=args.port,
                                user=args.user, password=args.password)
    conexion.set_session(readonly=True)
    try:
        with conexion.cursor() as cur:
            filas = inventariar(cur, tablas_py)
    finally:
        conexion.close()

    with open(salida, 'w', encoding='utf-8', newline='') as fh:
        escritor = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
        escritor.writeheader()
        escritor.writerows(filas)

    _resumen(filas, salida)


def _resumen(filas, salida):
    tablas = {f['tabla'] for f in filas}
    registros = sum({f['tabla']: f['filas_tabla'] for f in filas}.values())
    a_migrar = [f for f in filas if f['migrar'] == 'si']
    valores = sum(f['no_nulos'] for f in a_migrar)

    print("\n%-24s %s" % ("CSV generado:", os.path.normpath(salida)))
    print("%-24s %d" % ("Tablas de trámite:", len(tablas)))
    print("%-24s %d" % ("Registros totales:", registros))
    print("%-24s %d" % ("Columnas a migrar:", len(a_migrar)))
    print("%-24s %d" % ("Valores a migrar:", valores))
    print("%-24s %d" % ("Códigos distintos:", len({f['columna'] for f in a_migrar})))

    descartes = {}
    for fila in filas:
        if fila['migrar'] != 'si':
            descartes[fila['migrar']] = descartes.get(fila['migrar'], 0) + 1
    print("\nDescartadas: " + ", ".join("%s=%d" % kv for kv in sorted(descartes.items())))

    # Un mismo código con dos ttype distintos rompería el catálogo compartido.
    por_codigo = {}
    for fila in a_migrar:
        por_codigo.setdefault(fila['columna'], set()).add(
            (fila['ttype_inferido'], fila['comodel']))
    choques = {c: v for c, v in por_codigo.items() if len(v) > 1}
    if choques:
        print("\n!! COLISIONES DE TIPO (requieren sufijo por tipo):")
        for codigo, variantes in sorted(choques.items()):
            print("   %-24s %s" % (codigo, sorted(variantes)))
    else:
        print("\nSin colisiones de tipo entre tablas.")


if __name__ == '__main__':
    main()
