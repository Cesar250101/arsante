# -*- coding: utf-8 -*-
"""Definición de campos por tipo de registro.

Cada ``arsante.campo`` se materializa como un campo REAL en ``arsante.registro``
(``ir.model.fields`` con ``state='manual'``, prefijo ``x_arsante_``), de modo que
sea filtrable, agrupable y exportable como cualquier campo nativo.

Las columnas se comparten por código entre tipos: ``marca`` es la misma columna
en todos los tipos que la declaren, lo que permite agrupar y filtrar a través de
tipos distintos. La coherencia la garantiza ``_check_coherencia_codigo``.
"""

import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

from .plantilla import PREFIJO, nombre_tecnico

_logger = logging.getLogger(__name__)

RE_CODE = re.compile(r'^[a-z][a-z0-9_]{0,40}$')

TTYPES = [
    ('char', 'Texto'),
    ('text', 'Texto largo'),
    ('integer', 'Número entero'),
    ('float', 'Número decimal'),
    ('date', 'Fecha'),
    ('datetime', 'Fecha y hora'),
    ('boolean', 'Casilla (sí/no)'),
    ('binary', 'Archivo adjunto'),
    ('selection', 'Lista de opciones'),
    ('many2one', 'Relación'),
]

COMODELOS = [
    ('res.partner', 'Contacto (cliente, fabricante, proveedor…)'),
    ('product.product', 'Producto'),
    ('sale.order', 'Nota de venta'),
    ('account.move', 'Factura'),
    ('arsante.marcas', 'Marca'),
    ('res.company', 'Compañía'),
]

# A partir de este número de columnas se avisa al usuario. El límite duro de
# PostgreSQL es 1600 por tabla.
AVISO_COLUMNAS = 400


class ArsanteCampo(models.Model):
    _name = 'arsante.campo'
    _description = 'Definición de Campo por Tipo de Registro'
    _order = 'tipo_registro_id, sequence, id'

    tipo_registro_id = fields.Many2one(
        comodel_name='arsante.tipo_registro', string='Tipo de Registro',
        required=True, ondelete='cascade', index=True)
    name = fields.Char(string='Etiqueta', required=True,
                       help="Nombre que verá el usuario en el formulario.")
    code = fields.Char(
        string='Código', required=True,
        help="Identificador técnico, en minúsculas y sin espacios (ej. nro_oc).\n"
             "Los campos con el mismo código comparten columna entre tipos de "
             "registro, por lo que deben tener el mismo tipo de dato.\n"
             "Para cambiarlo después use el botón «Renombrar código».")
    field_name = fields.Char(
        string='Campo técnico', compute='_compute_field_name', store=True,
        help="Nombre real de la columna en la base de datos.")
    ttype = fields.Selection(
        selection=TTYPES, string='Tipo de dato', required=True, default='char',
        help="No se puede cambiar directamente: use el botón «Convertir tipo».")
    comodel_name = fields.Selection(
        selection=COMODELOS, string='Relacionado con')
    comodel_domain = fields.Char(
        string='Filtro', default='[]',
        help="Dominio Odoo que limita los registros seleccionables.")
    opcion_ids = fields.One2many(
        comodel_name='arsante.campo.opcion', inverse_name='campo_id',
        string='Opciones', copy=True)

    sequence = fields.Integer(string='Secuencia', default=10)
    seccion = fields.Selection(
        selection=[('izq', 'Columna izquierda'),
                   ('der', 'Columna derecha'),
                   ('extra', 'Pestaña «Información adicional»')],
        string='Ubicación', required=True, default='izq')

    requerido = fields.Boolean(
        string='Obligatorio',
        help="Obliga a rellenarlo en el formulario. No se aplica a los "
             "registros históricos ya existentes.")
    solo_lectura = fields.Boolean(string='Solo lectura')
    ayuda = fields.Text(string='Texto de ayuda')
    placeholder = fields.Char(string='Texto de ejemplo')
    widget = fields.Char(
        string='Widget',
        help="Widget de Odoo (url, image, many2many_tags…). Déjelo vacío salvo "
             "que sepa lo que hace.")

    mostrar_en_formulario = fields.Boolean(
        string='Mostrar en el formulario', default=True,
        help="Si lo desmarca, el campo deja de verse en el formulario pero "
             "conserva sus datos y se sigue pudiendo usar para buscar, agrupar "
             "y exportar.")
    mostrar_en_lista = fields.Boolean(string='Mostrar en la lista')
    mostrar_en_busqueda = fields.Boolean(string='Permitir buscar', default=True)
    agrupable = fields.Boolean(string='Permitir agrupar')
    indexado = fields.Boolean(
        string='Indexado',
        help="Acelera las búsquedas por este campo a costa de algo de espacio.")

    # Odoo no admite ondelete='restrict' hacia ir.model.fields. Con 'cascade'
    # la definición desaparece si alguien borra el campo real desde Ajustes:
    # es coherente, porque sin columna la definición no significa nada.
    ir_field_id = fields.Many2one(
        comodel_name='ir.model.fields', string='Campo real',
        readonly=True, copy=False, ondelete='cascade')
    es_nucleo = fields.Boolean(
        string='Campo estándar', readonly=True, copy=False,
        help="Campo común a todos los tipos de trámite (cliente, estado, "
             "facturado…). Se puede ocultar del formulario, pero no borrar ni "
             "cambiar de tipo: su columna la comparten los 20 tipos.")
    active = fields.Boolean(string='Activo', default=True)

    _sql_constraints = [
        ('tipo_code_uniq', 'unique(tipo_registro_id, code)',
         'Ya existe un campo con ese código en este tipo de registro.'),
    ]

    # ------------------------------------------------------------------
    # Cálculos y validaciones
    # ------------------------------------------------------------------

    @api.depends('code', 'es_nucleo')
    def _compute_field_name(self):
        for campo in self:
            if not campo.code:
                campo.field_name = False
            elif campo.es_nucleo:
                # Un campo estándar ya existe en el modelo: se referencia por su
                # nombre real, no se crea una columna nueva.
                campo.field_name = campo.code
            else:
                campo.field_name = nombre_tecnico(campo.code)

    @api.constrains('code')
    def _check_code(self):
        for campo in self:
            if not RE_CODE.match(campo.code or ''):
                raise ValidationError(_(
                    "El código «%s» no es válido. Debe empezar por una letra "
                    "minúscula y contener solo minúsculas, números y guiones "
                    "bajos (ej. nro_oc).", campo.code))
            # Chocar con un campo duro daría un campo inalcanzable: el resolutor
            # de plantillas siempre daría prioridad al campo del modelo. Los
            # campos de núcleo son justamente esos, así que se exceptúan.
            if not campo.es_nucleo and campo.code in self.env['arsante.registro']._fields:
                raise ValidationError(_(
                    "El código «%s» ya corresponde a un campo estándar del "
                    "registro. Elija otro.", campo.code))

    @api.constrains('code', 'ttype', 'comodel_name')
    def _check_coherencia_codigo(self):
        """Un mismo código es una misma columna: el tipo debe coincidir."""
        for campo in self:
            otros = self.search([
                ('code', '=', campo.code),
                ('id', '!=', campo.id),
            ])
            distintos = otros.filtered(
                lambda o: o.ttype != campo.ttype
                or (o.comodel_name or False) != (campo.comodel_name or False))
            if distintos:
                otro = distintos[0]
                raise ValidationError(_(
                    "El código «%(code)s» ya está definido como «%(tipo)s» en el "
                    "tipo de registro «%(tipo_reg)s». Los campos con el mismo "
                    "código comparten columna y deben tener el mismo tipo de "
                    "dato.\n\nUse otro código (por ejemplo «%(code)s_%(sufijo)s») "
                    "o cambie el tipo de dato allí.",
                    code=campo.code,
                    tipo=dict(TTYPES).get(otro.ttype, otro.ttype),
                    tipo_reg=otro.tipo_registro_id.name,
                    sufijo=(campo.tipo_registro_id.code or 'x')))

    @api.constrains('ttype', 'comodel_name')
    def _check_comodel(self):
        for campo in self:
            # En un campo estándar el modelo relacionado lo fija la definición
            # Python (company_id -> res.company, etc.), no esta configuración.
            if campo.es_nucleo:
                continue
            if campo.ttype == 'many2one' and not campo.comodel_name:
                raise ValidationError(_(
                    "El campo «%s» es una relación: indique con qué está "
                    "relacionado.", campo.name))

    @api.constrains('comodel_domain')
    def _check_domain(self):
        for campo in self:
            if not campo.comodel_domain:
                continue
            try:
                dominio = safe_eval(campo.comodel_domain)
                assert isinstance(dominio, (list, tuple))
            except Exception:
                raise ValidationError(_(
                    "El filtro del campo «%s» no es un dominio Odoo válido. "
                    "Ejemplo: [('customer_rank', '>', 0)]", campo.name))

    # ------------------------------------------------------------------
    # Sincronización con ir.model.fields
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        campos = super().create(vals_list)
        # En lote: un solo setup_models/init_models para todo el grupo, en vez
        # de uno por campo (cada uno cuesta 1-3 s con todos los módulos).
        campos._sync_ir_field()
        self._invalidar_vistas()
        return campos

    def write(self, vals):
        # Los asistentes de renombrar/convertir ya han hecho el trabajo pesado
        # sobre ir.model.fields; aquí sólo actualizan la definición.
        via_wizard = self.env.context.get('arsante_via_wizard')

        if not via_wizard and ('ttype' in vals or 'comodel_name' in vals):
            for campo in self:
                cambia = (vals.get('ttype', campo.ttype) != campo.ttype
                          or vals.get('comodel_name', campo.comodel_name)
                          != campo.comodel_name)
                if cambia and campo.ir_field_id:
                    raise UserError(_(
                        "Odoo no permite cambiar el tipo de dato de un campo ya "
                        "creado.\n\nUse el botón «Convertir tipo» del campo "
                        "«%s», que le indicará cuántos valores se perderían "
                        "antes de hacer nada.", campo.name))
        if not via_wizard and 'code' in vals:
            for campo in self:
                if campo.ir_field_id and vals['code'] != campo.code:
                    raise UserError(_(
                        "Para cambiar el código de «%s» use el botón «Renombrar "
                        "código», que conserva los datos ya guardados.",
                        campo.name))

        res = super().write(vals)
        # Sólo estas claves tienen reflejo en ir.model.fields; el resto (posición,
        # widget, obligatoriedad…) vive únicamente en la vista.
        if (not via_wizard
                and {'name', 'ayuda', 'indexado', 'comodel_domain',
                     'opcion_ids'} & set(vals)):
            self._sync_ir_field()
        self._invalidar_vistas()
        return res

    @api.ondelete(at_uninstall=False)
    def _check_datos_antes_de_borrar(self):
        if self.env.context.get('arsante_forzar_borrado'):
            return
        for campo in self:
            if campo.es_nucleo:
                raise UserError(_(
                    "«%s» es un campo estándar, común a todos los tipos de "
                    "trámite, y no se puede borrar. Si no lo necesita en este "
                    "tipo, desmarque «Mostrar en el formulario».", campo.name))
        for campo in self:
            usados = campo._contar_valores()
            if usados:
                raise UserError(_(
                    "El campo «%(name)s» tiene %(n)s valores guardados.\n\n"
                    "Si lo borra, esos datos se perderán. Le recomendamos "
                    "archivarlo (desmarcar «Activo»): desaparecerá de los "
                    "formularios pero conservará la información.",
                    name=campo.name, n=usados))

    def unlink(self):
        # Un campo de núcleo referencia el ir.model.fields del propio modelo
        # Python (state='base'): nunca se toca, sólo se deja de referenciar.
        campos_ir = self.filtered(lambda c: not c.es_nucleo).mapped('ir_field_id')
        res = super().unlink()
        # La columna sólo se elimina cuando ningún otro tipo de registro la usa.
        for ir_field in campos_ir:
            if not self.search_count([('ir_field_id', '=', ir_field.id)]):
                ir_field.sudo().unlink()
        self._invalidar_vistas()
        return res

    def _sync_ir_field(self):
        """Crea o actualiza el ir.model.fields de cada campo.

        Reutiliza la columna si ya existe (catálogo compartido por código), de
        modo que dos tipos que declaren ``marca`` compartan una única columna.
        """
        IrField = self.env['ir.model.fields'].sudo()
        model_id = self.env['ir.model']._get_id('arsante.registro')

        # Varios tipos de registro pueden declarar el mismo código: comparten
        # una única columna. Hay que agrupar por field_name antes de crear, o
        # el lote intentaría crear la misma columna varias veces y chocaría con
        # la restricción única (model, name) de ir_model_fields.
        a_crear = {}       # field_name -> vals
        pendientes = {}    # field_name -> [arsante.campo]
        a_enlazar = []
        for campo in self:
            if campo.es_nucleo:
                # El campo lo declara el modelo en Python: sólo se enlaza para
                # poder configurarlo, nunca se crea ni se modifica.
                if not campo.ir_field_id:
                    existente = IrField.search([
                        ('model', '=', 'arsante.registro'),
                        ('name', '=', campo.field_name)], limit=1)
                    if existente:
                        campo.ir_field_id = existente.id
                continue
            if campo.ir_field_id:
                campo._actualizar_ir_field()
                continue
            existente = IrField.search([
                ('model', '=', 'arsante.registro'),
                ('name', '=', campo.field_name),
            ], limit=1)
            if existente:
                a_enlazar.append((campo, existente))
                continue
            pendientes.setdefault(campo.field_name, []).append(campo)
            a_crear.setdefault(campo.field_name, campo._vals_ir_field(model_id))

        for campo, existente in a_enlazar:
            if existente.ttype != campo.ttype:
                raise ValidationError(_(
                    "La columna «%(col)s» ya existe con el tipo «%(actual)s» y "
                    "no se puede reutilizar como «%(nuevo)s».",
                    col=campo.field_name, actual=existente.ttype,
                    nuevo=campo.ttype))
            campo.ir_field_id = existente.id

        if a_crear:
            self._avisar_si_muchas_columnas(len(a_crear))
            nombres = list(a_crear)
            creados = IrField.create([a_crear[n] for n in nombres])
            for nombre, ir_field in zip(nombres, creados):
                for campo in pendientes[nombre]:
                    campo.ir_field_id = ir_field.id

        # Las opciones se escriben después de que exista el ir.model.fields.
        for campo in self.filtered(lambda c: c.ttype == 'selection'):
            campo._sync_opciones()

    def _vals_ir_field(self, model_id):
        self.ensure_one()
        vals = {
            'model_id': model_id,
            'name': self.field_name,
            'field_description': self.name,
            'help': self.ayuda or False,
            'ttype': self.ttype,
            'state': 'manual',
            'store': True,
            'copied': True,
            'index': self.indexado,
            # Nunca NOT NULL: la columna es común a todos los tipos de registro,
            # pero el campo pertenece a uno solo. Un required aquí rompería los
            # registros de los demás tipos. La obligatoriedad se aplica en la
            # vista (attrs) y al crear la nota de venta.
            'required': False,
            'readonly': False,
        }
        if self.ttype == 'many2one':
            vals.update({
                'relation': self.comodel_name,
                'on_delete': 'set null',
                'domain': self.comodel_domain or '[]',
            })
        return vals

    def _actualizar_ir_field(self):
        self.ensure_one()
        vals = {
            'field_description': self.name,
            'help': self.ayuda or False,
            'index': self.indexado,
        }
        if self.ttype == 'many2one':
            vals['domain'] = self.comodel_domain or '[]'
        self.ir_field_id.sudo().write(vals)
        if self.ttype == 'selection':
            self._sync_opciones()

    def _sync_opciones(self):
        """Vuelca opcion_ids en ir.model.fields.selection.

        Como la columna es compartida, las opciones son la UNIÓN de las que
        declaran todos los tipos que usan ese código: quitar una opción aquí no
        debe borrar los datos de otro tipo que sí la use.

        Se usa el ORM y no ``_update_selection``: ese método inserta con SQL
        directo (``query_insert``) y no dispara ``setup_models``, de modo que el
        campo se quedaría en el registry sin opciones y rechazaría cualquier
        valor con "Wrong value for ...". El create/write/unlink del ORM sí
        recarga el registry.
        """
        self.ensure_one()
        if not self.ir_field_id:
            return

        hermanos = self.search([('code', '=', self.code)])
        deseadas, vistos = [], set()
        for campo in hermanos:
            for opcion in campo.opcion_ids.sorted('sequence'):
                if opcion.code not in vistos:
                    vistos.add(opcion.code)
                    deseadas.append((opcion.code, opcion.name))
        if not deseadas:
            return

        Seleccion = self.env['ir.model.fields.selection'].sudo()
        actuales = {s.value: s for s in Seleccion.search(
            [('field_id', '=', self.ir_field_id.id)])}

        a_crear = []
        for indice, (valor, etiqueta) in enumerate(deseadas):
            existente = actuales.pop(valor, None)
            if existente:
                if existente.name != etiqueta or existente.sequence != indice:
                    existente.write({'name': etiqueta, 'sequence': indice})
            else:
                a_crear.append({'field_id': self.ir_field_id.id,
                                'value': valor, 'name': etiqueta,
                                'sequence': indice})
        if a_crear:
            Seleccion.create(a_crear)

        # Las que sobran se eliminan salvo que algún registro las esté usando:
        # borrarlas pondría a NULL esos valores (_process_ondelete).
        for valor, sobrante in actuales.items():
            self.env.cr.execute(
                'SELECT count(*) FROM arsante_registro WHERE "%s" = %%s'
                % self.field_name, (valor,))
            if self.env.cr.fetchone()[0]:
                _logger.info(
                    "arsante: se conserva la opción %r de %s porque hay "
                    "registros que la usan", valor, self.field_name)
                continue
            sobrante.unlink()

    def _contar_valores(self):
        """Nº de registros con valor en este campo. Los binary viven en adjuntos."""
        self.ensure_one()
        if not self.ir_field_id:
            return 0
        if self.ttype == 'binary':
            return self.env['ir.attachment'].sudo().search_count([
                ('res_model', '=', 'arsante.registro'),
                ('res_field', '=', self.field_name),
            ])
        self.env.cr.execute(
            'SELECT count("%s") FROM arsante_registro' % self.field_name)
        return self.env.cr.fetchone()[0]

    def _avisar_si_muchas_columnas(self, nuevas):
        total = self.env['ir.model.fields'].sudo().search_count([
            ('model', '=', 'arsante.registro'),
        ])
        if total + nuevas > AVISO_COLUMNAS:
            _logger.warning(
                "arsante.registro va a tener %d columnas (aviso a partir de %d, "
                "límite de PostgreSQL 1600).", total + nuevas, AVISO_COLUMNAS)

    def _invalidar_vistas(self):
        """El catálogo cambió: hay que rehacer las vistas inyectadas."""
        self.env['arsante.registro'].clear_caches()

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def action_abrir_formulario(self):
        """Abre la ficha completa del campo desde la lista editable.

        En la lista se marcan casillas; aquí se configuran las opciones de las
        listas desplegables, el texto de ayuda y el widget.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'arsante.campo',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_renombrar_codigo(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renombrar código'),
            'res_model': 'arsante.campo.renombrar',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_campo_id': self.id},
        }

    def action_convertir_tipo(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Convertir tipo de dato'),
            'res_model': 'arsante.campo.convertir',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_campo_id': self.id},
        }


class ArsanteCampoOpcion(models.Model):
    _name = 'arsante.campo.opcion'
    _description = 'Opción de Campo de Selección'
    _order = 'sequence, id'

    campo_id = fields.Many2one(
        comodel_name='arsante.campo', string='Campo',
        required=True, ondelete='cascade', index=True)
    name = fields.Char(string='Etiqueta', required=True)
    code = fields.Char(
        string='Valor', required=True,
        help="Valor almacenado en la base de datos. No lo cambie una vez haya "
             "registros usando esta opción.")
    sequence = fields.Integer(string='Secuencia', default=10)

    _sql_constraints = [
        ('campo_code_uniq', 'unique(campo_id, code)',
         'Ese valor ya existe en este campo.'),
    ]

    @api.constrains('code')
    def _check_code(self):
        """El valor es lo que se guarda en la columna.

        No se puede exigir un formato estricto: los datos existentes incluyen
        acentos ("inscripción_empresa") y espacios ("TODO MODA"), y rechazarlos
        haría imposible migrarlos o dejaría registros con el campo en blanco.
        """
        for opcion in self:
            valor = opcion.code or ''
            if not valor.strip():
                raise ValidationError(_("El valor de una opción no puede estar vacío."))
            if valor != valor.strip():
                raise ValidationError(_(
                    "El valor «%s» no puede empezar ni terminar con espacios.",
                    valor))
            if len(valor) > 128:
                raise ValidationError(_(
                    "El valor «%s» es demasiado largo (máximo 128 caracteres).",
                    valor[:40]))
