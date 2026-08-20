# -*- coding: utf-8 -*-
"""Genera el catálogo de campos dinámicos a partir del esquema legacy.

Se ejecuta en la fase ``post-``: los modelos nuevos ya existen y las 22 tablas
de trámite todavía no se han borrado (Odoo las elimina más tarde, en
``_process_end``), así que se puede leer su esquema real.

Reglas:
  * las columnas del núcleo pasan a ser campos duros de ``arsante.registro``
    y no generan definición;
  * las columnas 100 % vacías no se migran (se comprueba en ejecución, no con
    una lista fija: la base de producción cambia);
  * un mismo código comparte columna entre tipos, así que si el tipo de dato
    no coincide se le añade un sufijo por tipo y se reporta.
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

# Columnas que pasan a campos duros de arsante.registro, más las técnicas.
NUCLEO = {
    'id', 'create_uid', 'create_date', 'write_uid', 'write_date',
    'name', 'date', 'partner_id', 'product_id', 'tipo_registro_id',
    'estado', 'documentacion', 'facturado', 'no_cotizado', 'espera_resolucion',
    'requiere_renovacion', 'fecha_renovacion', 'alerta_renovacion',
    'nro_resolucion', 'comentario', 'sale_order_id', 'oc_facturacion',
    'active', 'importado',
}

# Los Many2one no se pueden deducir de information_schema (todos son integer).
COMODELOS = {
    'agente_aduana_id': 'res.partner',
    'fabricante_id': 'res.partner',
    'frabrante_id': 'res.partner',   # errata real en registro_dispositivos_medicos
    'proveedor_id': 'res.partner',
    'sale_id': 'sale.order',
}

# Opciones declaradas en los modelos Python, que desaparecen al borrarlos.
# En ejecución se UNEN con los valores realmente presentes en la base: hay
# columnas Selection con datos fuera de la lista declarada (p. ej. 161 de las
# 193 marcas de Inscripciones), que hoy se ven vacías en el formulario.
SELECCIONES = {
    'categoria': {
        'declaraciones': 'Declaraciones',
        'inscripción_empresa': 'Inscripción Empresa',
        'dec_sit_reg_dm': 'Decl situación regul. de DM',
        'rev_ant_dm': 'Revisión antecedentes que acompañan DM',
    },
    'etiqueta_lista': {'si': 'Sí', 'no': 'No', 'hacer': 'Hacer'},
    'eximicion': {'en_proceso': 'En Proceso', 'no': 'No',
                  'gestion': 'Gestionar', 'si': 'Sí'},
    'marca': {'no_aplica': 'No Aplica', 'todomoda': 'Todo Moda',
              'isadora': 'Isadora'},
    'marcar': {'no_aplica': 'No Aplica', 'todomoda': 'Todo Moda',
               'isadora': 'Isadora'},
    'mc_categoria': {
        'ampliacion_alcance': 'Ampliación Alcance',
        'ampliacion_colorantes': 'Ampliación Colorantes',
        'ampliacion_estudio_estabilidad': 'Ampliación estudio estabilidad',
        'ampliacion_isadora': 'Ampliación Isadora',
        'cambio_formula': 'Cambio de fórmula',
        'cambio_pais': 'Cambio de páis',
        'cambio_fabricante': 'Cambio fabricante',
        'modificacion_envase': 'Modificación Envase',
        'modificacion_especificaciones': 'Modificación especificaciones',
        'modificacion_formula': 'Modificación Fórmula',
    },
}

# Columnas que en el modelo eran binary (adjuntos): no tienen columna propia.
BINARIOS = {'pdf_nro_resolucion', 'pdf_resolucion', 'imagen'}

# Tablas que tienen tipo_registro_id pero NO son trámites: son las del propio
# sistema genérico y la consolidada. Sin excluirlas, arsante_campo acabaría
# migrándose a sí misma como si fuera un trámite.
EXCLUIDAS = ('arsante_all_record', 'arsante_registro', 'arsante_campo',
             'arsante_campo_opcion')

# Un campo sólo se migra como lista de opciones si los valores realmente
# guardados son pocos. Varias columnas están declaradas como Selection en el
# código pero contienen texto libre: "categoria" tiene 469 valores distintos y
# "marca" 63, frente a las 4 y 3 opciones declaradas. Convertirlas en Selection
# dejaría esos valores fuera de la lista y, aunque siguen en la base, el
# formulario los mostraría vacíos (es lo que ya pasa hoy con 161 marcas de
# Inscripciones). Por encima de este umbral se migran como texto.
UMBRAL_SELECTION = 30

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

# Etiquetas legibles para los códigos más frecuentes. El resto se genera
# a partir del código.
ETIQUETAS = {
    'au': 'AU', 'nro_cda': 'Nro. CDA', 'nro_uyd': 'Nro. UYD',
    'nro_isp': 'Nro. ISP', 'nro_oc': 'Nro. OC', 'nro_registro': 'Nro. Registro',
    'ref_gicona': 'Ref. Gicona', 'refgicona': 'Ref. Gicona',
    'ref_gicona_isp': 'Ref. Gicona ISP', 'ref_isp': 'Ref. ISP',
    'ref_tramite': 'Ref. Trámite', 'ref_solicitud': 'Ref. Solicitud',
    'fabricante_id': 'Nombre Fabricante', 'proveedor_id': 'Proveedor',
    'agente_aduana_id': 'Agente de Aduana', 'frabrante_id': 'Fabricante',
    'marca': 'Marca', 'marcar': 'Marca', 'categoria': 'Categoría',
    'mc_categoria': 'Categoría', 'mc_nro_registro': 'Nro. Registro',
    'mc_ref_gicona': 'Ref. Gicona', 'correo_ids': 'Correos Electrónicos',
    'fecha_llegada': 'Fecha de Llegada', 'fecha_resolucion': 'Fecha Resolución',
    'fecha_vcto': 'Fecha Vencimiento', 'fecha_ingreso': 'Fecha de Ingreso',
    'item': 'Item', 'sku': 'SKU', 'oc': 'OC', 'bl': 'BL',
}


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    # NUCLEO es la foto de los campos duros tal como eran en 2.0.0. Migraciones
    # posteriores ascienden más columnas a campo duro (nro_uyd en 2.1.3,
    # marca_bijou en 2.1.2), y esta migración se ejecuta antes que ellas: sin
    # esto intentaría catalogar como dinámico un código que el modelo actual ya
    # define, y _check_code aborta la carga del registro entero. Se consulta el
    # modelo en vivo para que cualquier ascenso futuro quede cubierto solo.
    duros = set(env['arsante.registro']._fields) - NUCLEO
    if duros:
        NUCLEO.update(duros)
        _logger.info(
            "arsante: %d columnas son ya campos duros del registro y no se "
            "catalogan como dinámicas (%s)",
            len(duros), ", ".join(sorted(duros)))

    tablas = _tablas_tramite(cr)
    if not tablas:
        _logger.warning("arsante: no hay tablas de trámite que catalogar")
        return

    tipos = _mapa_tipos(env, tablas)
    columnas = _recolectar(cr, tablas)
    valores = _valores_reales(cr, tablas)
    plan, choques = _planificar(columnas, tipos, valores)

    if not plan:
        _logger.warning("arsante: no se generó ninguna definición de campo")
        return

    # Idempotente: si una ejecución anterior de esta misma migración llegó a
    # crear parte del catálogo y se interrumpió después (p. ej. por un fallo
    # ajeno más adelante en la carga de módulos, con el commit intermedio ya
    # hecho), un segundo intento no debe reventar por duplicados — se salta lo
    # que ya existe y sólo crea lo que falta.
    existentes = set(
        env['arsante.campo'].with_context(active_test=False)
        .search([]).mapped(lambda c: (c.tipo_registro_id.id, c.code)))
    if existentes:
        antes = len(plan)
        plan = [v for v in plan
                if (v['tipo_registro_id'], v['code']) not in existentes]
        if antes != len(plan):
            _logger.info("arsante: %d definiciones ya existían de una "
                         "ejecución anterior, se omiten", antes - len(plan))

    if not plan:
        _logger.info("arsante: el catálogo de campos ya estaba completo")
        return

    # Un solo create en lote: cada create de ir.model.fields dispara un
    # setup_models completo (1-3 s), así que hacerlo campo a campo costaría
    # varios minutos.
    campos = env['arsante.campo'].create(plan)
    _logger.info("arsante: creadas %d definiciones de campo sobre %d códigos "
                 "distintos", len(campos), len({v['code'] for v in plan}))

    for aviso in choques:
        _logger.warning("arsante: %s", aviso)

    cr.execute("""
        CREATE TABLE IF NOT EXISTS arsante_backup.informe (
            momento text, detalle text, ts timestamp DEFAULT now())
    """)
    for aviso in choques:
        cr.execute("INSERT INTO arsante_backup.informe (momento, detalle) "
                   "VALUES ('catalogo', %s)", (aviso,))


def _tablas_tramite(cr):
    cr.execute("""
        SELECT DISTINCT table_name FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name LIKE 'arsante!_%%' ESCAPE '!'
           AND table_name NOT LIKE '%%!_wizard' ESCAPE '!'
           AND column_name = 'tipo_registro_id'
           AND table_name NOT IN %s
         ORDER BY 1
    """, (EXCLUIDAS,))
    return [r[0] for r in cr.fetchall()]


def _mapa_tipos(env, tablas):
    """tabla legacy -> id de arsante.tipo_registro.

    El tipo se toma del modelo de origen y no del valor de cada fila: una fila
    con el tipo cruzado dejaría sus datos específicos invisibles en el
    formulario del tipo equivocado.
    """
    mapa = {}
    for tabla in tablas:
        modelo = tabla.replace('_', '.', 1)
        env.cr.execute(
            'SELECT tipo_registro_id, count(*) FROM public."%s" '
            'WHERE tipo_registro_id IS NOT NULL '
            'GROUP BY 1 ORDER BY 2 DESC LIMIT 1' % tabla)
        fila = env.cr.fetchone()
        if fila:
            mapa[tabla] = fila[0]
            continue
        # Tabla vacía: se deduce del Selection tipo del catálogo maestro.
        clave = tabla[len('arsante_'):]
        tipo = env['arsante.tipo_registro'].search([('tipo', '=', clave)], limit=1)
        if tipo:
            mapa[tabla] = tipo.id
        else:
            _logger.info("arsante: %s sin tipo de registro asociado, se omite "
                         "del catálogo", modelo)
    return mapa


def _recolectar(cr, tablas):
    """[(tabla, columna, data_type, no_nulos)] de lo que puede ser campo."""
    filas = []
    for tabla in tablas:
        cr.execute("""
            SELECT column_name, data_type FROM information_schema.columns
             WHERE table_schema='public' AND table_name=%s
             ORDER BY ordinal_position
        """, (tabla,))
        for columna, tipo_pg in cr.fetchall():
            if columna in NUCLEO:
                continue
            cr.execute('SELECT count("%s") FROM public."%s"' % (columna, tabla))
            no_nulos = cr.fetchone()[0]
            if not no_nulos:
                continue  # columna sin un solo dato: no merece un campo
            filas.append((tabla, columna, tipo_pg, no_nulos))

    filas.extend(_recolectar_binarios(cr, tablas))
    return filas


def _recolectar_binarios(cr, tablas):
    """Campos Binary con adjuntos.

    Un Binary manual (y los del código legacy) usa ``attachment=True``: no tiene
    columna, así que information_schema no lo ve. Sus datos viven en
    ir_attachment, de donde se deducen aquí. Sin esto, los 1.101 PDF de
    resolución se quedarían sin campo de destino y post-50 no podría moverlos.
    """
    modelos = {t: t.replace('_', '.', 1) for t in tablas}
    cr.execute("""
        SELECT res_model, res_field, count(*)
          FROM ir_attachment
         WHERE res_model LIKE 'arsante.%%' AND res_field IS NOT NULL
         GROUP BY 1, 2
    """)
    por_modelo = {(m, f): n for m, f, n in cr.fetchall()}

    filas = []
    for tabla, modelo in modelos.items():
        for (mod, campo), n in por_modelo.items():
            if mod == modelo and campo not in NUCLEO:
                filas.append((tabla, campo, '__binary__', n))
    return filas


def _valores_reales(cr, tablas):
    """{columna: set(valores)} de las columnas candidatas a lista de opciones.

    Se consultan los datos y no sólo la declaración del modelo: es la única
    forma de saber si una columna es de verdad una lista cerrada.
    """
    valores = {}
    for columna in SELECCIONES:
        encontrados = set()
        for tabla in tablas:
            cr.execute("""SELECT 1 FROM information_schema.columns
                           WHERE table_schema='public' AND table_name=%s
                             AND column_name=%s""", (tabla, columna))
            if not cr.fetchone():
                continue
            cr.execute('SELECT DISTINCT "%s" FROM public."%s" WHERE "%s" IS NOT NULL'
                       % (columna, tabla, columna))
            encontrados.update(r[0] for r in cr.fetchall() if r[0] != '')
        valores[columna] = encontrados
    return valores


def _planificar(columnas, tipos, valores):
    """Convierte las columnas en vals de arsante.campo, resolviendo choques."""
    plan, choques = [], []
    tipo_por_codigo = {}   # code -> (ttype, comodel)
    vistos = set()         # (tipo_registro_id, code)

    for tabla, columna, tipo_pg, no_nulos in sorted(columnas):
        if tabla not in tipos:
            continue
        code = columna.lower()
        ttype, comodel = _inferir(columna, tipo_pg, valores)

        anterior = tipo_por_codigo.get(code)
        if anterior and anterior != (ttype, comodel):
            # Mismo código con distinto tipo: no pueden compartir columna.
            sufijo = tabla[len('arsante_'):][:20]
            code = '%s__%s' % (code, sufijo)
            choques.append(
                "El código «%s» de %s usa el tipo %s mientras que otro tipo lo "
                "define como %s; se migra como «%s»."
                % (columna, tabla, ttype, anterior[0], code))
        tipo_por_codigo.setdefault(code, (ttype, comodel))

        clave = (tipos[tabla], code)
        if clave in vistos:
            continue
        vistos.add(clave)

        vals = {
            'tipo_registro_id': tipos[tabla],
            'name': ETIQUETAS.get(columna, _etiqueta(columna)),
            'code': code,
            'ttype': ttype,
            'seccion': 'izq',
            'sequence': 10,
            'mostrar_en_busqueda': True,
            'mostrar_en_lista': ttype not in ('text', 'binary'),
            'agrupable': ttype in ('selection', 'many2one', 'boolean'),
        }
        if comodel:
            vals['comodel_name'] = comodel
        if ttype == 'selection':
            vals['opcion_ids'] = _opciones(columna, valores)
        plan.append(vals)

    return plan, choques


def _inferir(columna, tipo_pg, valores):
    if tipo_pg == '__binary__' or columna in BINARIOS:
        return 'binary', None
    if columna in SELECCIONES:
        # Lista cerrada sólo si los datos reales son pocos; si no, texto.
        if len(valores.get(columna, ())) <= UMBRAL_SELECTION:
            return 'selection', None
        return 'char', None
    if columna in COMODELOS:
        return 'many2one', COMODELOS[columna]
    if tipo_pg == 'integer' and columna.endswith('_id'):
        # Un *_id sin comodel conocido no se puede convertir en relación.
        return 'integer', None
    return MAPA_PG.get(tipo_pg, 'char'), None


def _opciones(columna, valores):
    """Opciones declaradas UNIDAS a los valores que existen en la base.

    Sin la unión, cualquier valor guardado que no estuviera declarado se
    mostraría vacío en el formulario aunque siga en la base de datos. Los
    valores sin etiqueta declarada se rotulan con su propio valor.
    """
    declaradas = dict(SELECCIONES.get(columna, {}))
    opciones = list(declaradas.items())
    conocidos = set(declaradas)
    for valor in sorted(valores.get(columna, ())):
        if valor not in conocidos:
            opciones.append((valor, valor))
    return [(0, 0, {'code': code, 'name': etiqueta, 'sequence': (i + 1) * 10})
            for i, (code, etiqueta) in enumerate(opciones)]


def _etiqueta(columna):
    return columna.replace('_', ' ').strip().capitalize()
