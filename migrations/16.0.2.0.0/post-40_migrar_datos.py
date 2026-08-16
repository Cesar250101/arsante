# -*- coding: utf-8 -*-
"""Copia los 2.434 registros de las 22 tablas de trámite a ``arsante_registro``.

Se hace con SQL directo y no con el ORM: 2.434 ``create()`` dispararían los
computes (entre ellos ``_compute_name``, que reescribiría los nombres que hoy
ven los usuarios) y tardarían minutos. El INSERT ... SELECT preserva además
``create_uid``/``create_date``/``write_uid``/``write_date``, de modo que la
trazabilidad de auditoría no se pierde.

El ``tipo_registro_id`` se toma del mapa modelo -> tipo y no del valor de cada
fila: hay una fila cruzada en ``registro_cosmetico`` cuyos datos específicos
quedarían invisibles si se abriera con el formulario del tipo equivocado. La
divergencia se anota en el informe.
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

ESQUEMA = 'arsante_backup'

# Tablas con tipo_registro_id que NO son trámites: las del propio sistema
# genérico y la consolidada.
EXCLUIDAS = ('arsante_all_record', 'arsante_registro', 'arsante_campo',
             'arsante_campo_opcion')

# Columna legacy -> columna del modelo genérico. El resto de columnas del
# núcleo se llaman igual en ambos lados.
EQUIVALENCIAS = {
    'comentarios': 'comentario',   # exim_proceso_cosmeticos y registro_isp*
    'sale_id': 'sale_order_id',    # registro_isp*
}

NUCLEO = [
    'name', 'date', 'partner_id', 'product_id', 'estado', 'documentacion',
    'facturado', 'no_cotizado', 'espera_resolucion', 'requiere_renovacion',
    'fecha_renovacion', 'alerta_renovacion', 'nro_resolucion', 'comentario',
    'sale_order_id', 'oc_facturacion', 'active',
]

BOOLEANOS = {
    'facturado', 'no_cotizado', 'espera_resolucion', 'requiere_renovacion',
    'alerta_renovacion', 'active',
}


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    campos = _catalogo_por_tipo(env)
    if not campos:
        _logger.warning("arsante: no hay catálogo de campos; nada que migrar")
        return

    empresa = _empresa_por_defecto(cr)
    total = 0
    for tabla, tipo_id in _tablas_y_tipos(cr, env).items():
        total += _migrar_tabla(cr, tabla, tipo_id, campos.get(tipo_id, {}), empresa)

    cr.execute("SELECT setval(pg_get_serial_sequence('arsante_registro','id'), "
               "GREATEST((SELECT max(id) FROM arsante_registro), 1))")

    cr.execute("SELECT count(*) FROM arsante_registro")
    _logger.info("arsante: migrados %d registros (%d filas en arsante_registro)",
                 total, cr.fetchone()[0])

    _anotar_divergencias(cr)


def _catalogo_por_tipo(env):
    """{tipo_registro_id: {code: field_name}} de los campos ESPECÍFICOS.

    Se excluyen los de núcleo (es_nucleo=True, ej. 'date'/'estado'): su dato ya
    lo copia el bloque NUCLEO de _migrar_tabla con su propio mapeo de columnas
    legacy. Incluirlos aquí también duplicaría la columna en el INSERT (y, si
    esta migración ya corrió una vez —16.0.2.1.0 ya sembró esos campos—,
    revienta con "column specified more than once").
    """
    catalogo = {}
    campos = env['arsante.campo'].search([('es_nucleo', '=', False)])
    for campo in campos:
        catalogo.setdefault(campo.tipo_registro_id.id, {})[campo.code] = campo.field_name
    return catalogo


def _empresa_por_defecto(cr):
    cr.execute("SELECT id FROM res_company WHERE es_arsante ORDER BY id LIMIT 1")
    fila = cr.fetchone()
    if fila:
        return fila[0]
    cr.execute("SELECT id FROM res_company ORDER BY id LIMIT 1")
    return cr.fetchone()[0]


def _tablas_y_tipos(cr, env):
    cr.execute("""
        SELECT DISTINCT table_name FROM information_schema.columns
         WHERE table_schema='public' AND table_name LIKE 'arsante!_%%' ESCAPE '!'
           AND table_name NOT LIKE '%%!_wizard' ESCAPE '!'
           AND column_name='tipo_registro_id'
           AND table_name NOT IN %s
         ORDER BY 1
    """, (EXCLUIDAS,))
    resultado = {}
    for (tabla,) in cr.fetchall():
        cr.execute('SELECT tipo_registro_id, count(*) FROM public."%s" '
                   'WHERE tipo_registro_id IS NOT NULL GROUP BY 1 '
                   'ORDER BY 2 DESC LIMIT 1' % tabla)
        fila = cr.fetchone()
        if fila:
            resultado[tabla] = fila[0]
            continue
        clave = tabla[len('arsante_'):]
        tipo = env['arsante.tipo_registro'].search([('tipo', '=', clave)], limit=1)
        if tipo:
            resultado[tabla] = tipo.id
    return resultado


def _columnas(cr, tabla):
    cr.execute("""SELECT column_name FROM information_schema.columns
                   WHERE table_schema='public' AND table_name=%s""", (tabla,))
    return {r[0] for r in cr.fetchall()}


def _migrar_tabla(cr, tabla, tipo_id, campos, empresa):
    existentes = _columnas(cr, tabla)
    modelo = tabla.replace('_', '.', 1)

    destino = ['tipo_registro_id', 'company_id', 'legacy_model', 'legacy_id',
               'create_uid', 'create_date', 'write_uid', 'write_date']
    origen = ['%(tipo)s', '%(empresa)s', '%(modelo)s', 't.id',
              't.create_uid', 't.create_date', 't.write_uid', 't.write_date']

    for columna in NUCLEO:
        fuente = _fuente(columna, existentes)
        if not fuente:
            continue
        destino.append(columna)
        if columna in BOOLEANOS:
            origen.append('COALESCE(t."%s", %s)'
                          % (fuente, 'true' if columna == 'active' else 'false'))
        else:
            origen.append('t."%s"' % fuente)

    # Campos específicos: del código de arsante.campo a su columna x_arsante_*.
    for code, field_name in sorted(campos.items()):
        # El código puede llevar sufijo por colisión de tipo (code__tabla).
        columna = code.split('__')[0]
        if columna not in existentes:
            continue
        cr.execute("""SELECT count(*) FROM information_schema.columns
                       WHERE table_name='arsante_registro' AND column_name=%s""",
                   (field_name,))
        if not cr.fetchone()[0]:
            continue  # binary: vive en ir_attachment, lo mueve post-50
        destino.append(field_name)
        origen.append('t."%s"' % columna)

    # Idempotente: si una ejecución anterior ya migró esta tabla (commit
    # intermedio de Odoo + fallo posterior ajeno, más adelante en la carga de
    # módulos), un segundo intento no debe violar legacy_uniq — se omiten las
    # filas cuyo (legacy_model, legacy_id) ya están en arsante_registro.
    consulta = """
        INSERT INTO arsante_registro (%s)
        SELECT %s FROM public."%s" t
        WHERE NOT EXISTS (
            SELECT 1 FROM arsante_registro r
             WHERE r.legacy_model = %%(modelo)s AND r.legacy_id = t.id)
        ORDER BY t.id
        RETURNING id, legacy_id
    """ % (', '.join('"%s"' % c for c in destino), ', '.join(origen), tabla)

    cr.execute(consulta, {'tipo': tipo_id, 'empresa': empresa, 'modelo': modelo})
    filas = cr.fetchall()

    if filas:
        # El mapa permite remapear los adjuntos y auditar la migración después.
        cr.executemany(
            "INSERT INTO %s.mapa_ids (legacy_model, legacy_id, nuevo_id) "
            "VALUES (%%s, %%s, %%s)" % ESQUEMA,
            [(modelo, legacy, nuevo) for nuevo, legacy in filas])

    _logger.info("arsante: %-45s -> %4d registros", tabla, len(filas))
    return len(filas)


def _fuente(columna, existentes):
    """Nombre de la columna legacy equivalente, si existe."""
    if columna in existentes:
        return columna
    for legacy, generico in EQUIVALENCIAS.items():
        if generico == columna and legacy in existentes:
            return legacy
    return None


def _anotar_divergencias(cr):
    """Registra las filas cuyo tipo original no coincide con el del modelo."""
    cr.execute("""
        CREATE TABLE IF NOT EXISTS arsante_backup.informe (
            momento text, detalle text, ts timestamp DEFAULT now())
    """)
    cr.execute("SELECT legacy_model, legacy_id, nuevo_id FROM %s.mapa_ids"
               % ESQUEMA)
    for modelo, legacy_id, nuevo_id in cr.fetchall():
        tabla = modelo.replace('.', '_', 1)
        try:
            cr.execute('SELECT tipo_registro_id FROM public."%s" WHERE id=%%s'
                       % tabla, (legacy_id,))
            fila = cr.fetchone()
        except Exception:
            continue
        if not fila or not fila[0]:
            continue
        cr.execute("SELECT tipo_registro_id FROM arsante_registro WHERE id=%s",
                   (nuevo_id,))
        nuevo_tipo = cr.fetchone()[0]
        if fila[0] != nuevo_tipo:
            cr.execute(
                "INSERT INTO arsante_backup.informe (momento, detalle) "
                "VALUES ('migracion', %s)",
                ("%s id=%s tenía tipo_registro_id=%s y se migró al tipo %s "
                 "del modelo (registro nuevo id=%s); revisar manualmente."
                 % (modelo, legacy_id, fila[0], nuevo_tipo, nuevo_id),))
