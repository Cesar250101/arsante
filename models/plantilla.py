# -*- coding: utf-8 -*-
"""Motor de plantillas de texto de arsante.

Sustituye ``{codigo}`` por el valor formateado del campo correspondiente de un
``arsante.registro``. Se usa en dos sitios:

  * ``arsante.tipo_registro.name_template``    -> nombre del registro
  * ``arsante.tipo_registro.so_line_template`` -> texto de la línea de venta

Sustituye a los 20 métodos ``create_so()`` que concatenaban campos a mano, uno
por modelo de trámite.

Seguridad: NO se usa ``eval`` ni ``str.format``/``format_map``. ``format_map``
seguiría exponiendo ``{a.b}``, ``{a[0]}``, ``{a!r}`` y las format-spec, que dan
acceso a atributos arbitrarios del recordset. Aquí sólo se acepta un
identificador plano, validado por la expresión regular.
"""

import re

from odoo.tools.misc import format_date, format_datetime

# Un identificador plano, con un único modificador opcional: sin puntos,
# índices, conversiones de Python ni format-specs.
#   {nro_oc}        -> valor formateado (un selection da su etiqueta)
#   {marca|raw}     -> valor tal cual está guardado (un selection da su código)
# El modificador existe para reproducir literalmente las líneas de venta
# históricas, que concatenaban el código del selection ("MARCA:todomoda") y no
# su etiqueta ("MARCA:Todo Moda").
PATRON = re.compile(r'\{([a-z][a-z0-9_]{0,40})(\|raw)?\}')

PREFIJO = 'x_arsante_'


def nombre_tecnico(code):
    """Código de usuario -> nombre real de la columna. 'nro_oc' -> 'x_arsante_nro_oc'."""
    return PREFIJO + code


def resolver_campo(record, code):
    """Devuelve el nombre del campo real para ``code``, o None si no existe.

    Prioridad: campo duro del modelo, luego campo dinámico. Así ``partner_id``
    resuelve al campo duro aunque alguien cree un ``arsante.campo`` homónimo.
    """
    if code in record._fields:
        return code
    tecnico = nombre_tecnico(code)
    if tecnico in record._fields:
        return tecnico
    return None


def valor_bruto(record, code):
    """Valor sin formatear, o False si el código no corresponde a ningún campo."""
    nombre = resolver_campo(record, code)
    return record[nombre] if nombre else False


def valor_str(record, code):
    """Valor formateado como texto para insertar en una plantilla.

    Un código inexistente o un valor vacío dan cadena vacía: una plantilla nunca
    debe reventar al renderizarse durante la facturación.
    """
    nombre = resolver_campo(record, code)
    if not nombre:
        return ''
    valor = record[nombre]
    if valor is False or valor is None or valor == '':
        return ''

    campo = record._fields[nombre]
    tipo = campo.type

    if tipo == 'many2one':
        return valor.display_name or ''
    if tipo in ('one2many', 'many2many'):
        return ', '.join(valor.mapped('display_name'))
    if tipo == 'selection':
        etiquetas = dict(campo._description_selection(record.env))
        return etiquetas.get(valor, valor) or ''
    if tipo == 'date':
        return format_date(record.env, valor)
    if tipo == 'datetime':
        return format_datetime(record.env, valor)
    if tipo == 'boolean':
        return 'Sí' if valor else ''
    if tipo == 'binary':
        # El contenido de un adjunto nunca va en un texto.
        return ''
    if tipo in ('integer', 'float', 'monetary'):
        # 0 se considera "sin dato", igual que hacía el código original.
        return str(valor) if valor else ''
    return str(valor)


def valor_raw_str(record, code):
    """Valor tal cual está almacenado, como texto. Un selection da su código."""
    valor = valor_bruto(record, code)
    if valor is False or valor is None or valor == '':
        return ''
    nombre = resolver_campo(record, code)
    tipo = record._fields[nombre].type
    if tipo == 'many2one':
        return valor.display_name or ''
    if tipo in ('integer', 'float', 'monetary'):
        return str(valor) if valor else ''
    if tipo == 'boolean':
        return 'Sí' if valor else ''
    if tipo == 'binary':
        return ''
    return str(valor)


def render(record, plantilla):
    """Renderiza ``plantilla`` sobre ``record``. Colapsa los huecos que dejan los
    códigos vacíos para no producir textos con espacios dobles."""
    if not plantilla:
        return ''

    def _sub(m):
        code, crudo = m.group(1), m.group(2)
        return (valor_raw_str(record, code) if crudo
                else valor_str(record, code))

    texto = PATRON.sub(_sub, plantilla)
    return re.sub(r'\s{2,}', ' ', texto).strip()


def codigos_usados(plantilla):
    """Códigos referenciados por una plantilla. Se usa para validarla al guardar."""
    return {m[0] for m in PATRON.findall(plantilla or '')}
