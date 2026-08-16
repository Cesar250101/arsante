# -*- coding: utf-8 -*-
"""Modelo genérico de trámite.

Sustituye a los 22 modelos ``arsante.<tramite>`` que existían antes, uno por
tipo de registro. Los campos comunes a todos los trámites son campos duros de
este modelo; los específicos de cada tipo se definen desde la interfaz como
``arsante.campo`` y se inyectan en las vistas en tiempo de ejecución.

Sobre la inyección: los nombres de los campos dinámicos NUNCA se escriben en un
``arch_db`` almacenado. Si lo hiciéramos, ``ir.model.fields._prepare_update``
bloquearía renombrar o borrar cualquier campo que apareciese en una vista
guardada. Por eso se sobrescribe ``_get_view`` en vez de generar vistas.
"""

import logging

from lxml import etree

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError

from . import plantilla

_logger = logging.getLogger(__name__)

# Dónde se inyecta cada sección declarada en arsante.campo.seccion.
ANCLAS_FORM = {
    'izq': 'arsante_campos_izq',
    'der': 'arsante_campos_der',
    'extra': 'arsante_campos_extra',
}

# Marca los nodos generados para poder rehacer la inyección sin duplicar.
MARCA = 'data-arsante-generado'

# URLs de las carpetas de colillas de pago por marca (SharePoint), tal cual las
# tenían cda_cosmetico_dm.py, rev_antecedentes_dm.py y demás modelos legacy.
MARCA_BIJOU_URLS = {
    'todomoda': 'https://arsanteconsultores-my.sharepoint.com/personal/pmuquillaza_arsante_cl/_layouts/15/onedrive.aspx?id=%2Fpersonal%2Fpmuquillaza%5Farsante%5Fcl%2FDocuments%2F1%2E%20CLIENTES%20VIGENTES%20AR%20SANTE%202025%2F0%2E%20COLILLAS%20DE%20PAGO%20BIJOU%2FBIJOU%2F2%2E%20colillas%20de%20pago%20TODO%20MODA&ga=1',
    'isadora': 'https://arsanteconsultores-my.sharepoint.com/personal/pmuquillaza_arsante_cl/_layouts/15/onedrive.aspx?id=%2Fpersonal%2Fpmuquillaza%5Farsante%5Fcl%2FDocuments%2F1%2E%20CLIENTES%20VIGENTES%20AR%20SANTE%202025%2F0%2E%20COLILLAS%20DE%20PAGO%20BIJOU%2FBIJOU%2F1%2E%20colillas%20de%20pago%20ISADORA&ga=1',
}

# Campos de núcleo que necesitan algo más que un <field> simple: un botón
# contextual que depende de otro campo. field_name -> configuración del botón.
CAMPOS_CON_BOTON = {
    'marca_bijou': {
        'campo_url': 'marca_bijou_url',
        'metodo': 'action_abrir_marca_bijou',
        'boton_string': 'URL OneDrive',
        'icono': 'fa-folder-open',
    },
}


class ArsanteRegistro(models.Model):
    _name = 'arsante.registro'
    _description = 'Registro / Trámite Arsante'
    _order = 'date desc, id desc'

    # ------------------------------------------------------------------
    # Campos comunes a todos los tipos de trámite
    # ------------------------------------------------------------------

    tipo_registro_id = fields.Many2one(
        comodel_name='arsante.tipo_registro', string='Tipo de Registro',
        required=True, index=True, ondelete='restrict')
    name = fields.Char(
        string='Nombre Registro', compute='_compute_name',
        store=True, readonly=False)
    date = fields.Date(string='Fecha Registro')
    partner_id = fields.Many2one(
        comodel_name='res.partner', string='Cliente', index=True,
        domain="['|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]")
    product_id = fields.Many2one(
        comodel_name='product.product', string='Producto',
        domain="['|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]")

    estado = fields.Selection(
        selection=[('listo', 'Listo'), ('no_listo', 'No Listo')], string='Estado')
    documentacion = fields.Selection(
        selection=[('completa', 'Completa'), ('incompleta', 'Incompleta')],
        string='Documentación')
    facturado = fields.Boolean(string='Facturado', index=True)
    no_cotizado = fields.Boolean(string='No Cotizado?')
    espera_resolucion = fields.Boolean(string='Espera de resolución?')

    requiere_renovacion = fields.Boolean(string='Requiere Renovación?')
    fecha_renovacion = fields.Date(string='Fecha de Renovación')
    alerta_renovacion = fields.Boolean(
        string='Alerta Renovación?', compute='_compute_alerta_renovacion',
        store=True)

    nro_resolucion = fields.Char(string='Nro. Resolución')
    nro_uyd = fields.Char(string='Nº UYD')
    comentario = fields.Text(string='Comentario')
    imagen = fields.Binary(string='Imagen', attachment=True)

    sale_order_id = fields.Many2one(
        comodel_name='sale.order', string='Nota de Venta',
        index=True, ondelete='set null')
    oc_facturacion = fields.Char(string='OC Facturación')
    invoice_ids = fields.Many2many(
        comodel_name='account.move', string='Facturas',
        related='sale_order_id.invoice_ids', readonly=True)

    active = fields.Boolean(string='Activo', default=True)
    company_id = fields.Many2one(
        comodel_name='res.company', string='Compañía', index=True,
        default=lambda self: self.env.company)

    # Clasificación bijoutería (Todo Moda / Isadora), con el enlace a la
    # carpeta de colillas de pago correspondiente — mismo comportamiento que
    # el campo "marca" de cda_cosmetico_dm.py, rev_antecedentes_dm.py, etc.
    #
    # El nombre técnico NO es "marca" a propósito: ese código ya lo usan, como
    # campo propio de tipo Texto libre, los 8 tipos migrados desde modelos cuya
    # columna "marca" tenía más de 30 valores reales distintos (nombres de
    # productos cosméticos: "SKINFOOD", "TODOMODA", "BUBBALUU"…). Si este campo
    # se llamara igual, esos datos migrados quedarían inalcanzables por código
    # — y "Nro. OC: {marca}" en la plantilla de CDA Cosméticos empezaría a
    # resolver contra este campo vacío en vez de contra el dato real.
    marca_bijou = fields.Selection([
        ('no_aplica', 'No Aplica'),
        ('todomoda', 'Todo Moda'),
        ('isadora', 'Isadora'),
    ], string='Marca')
    marca_bijou_url = fields.Char(
        string='URL OneDrive', compute='_compute_marca_bijou_url')

    # Trazabilidad permanente al modelo de origen tras la migración. No es sólo
    # para el proceso de migración: permite auditar de dónde vino cada registro.
    legacy_model = fields.Char(string='Modelo de origen', readonly=True, index=True)
    legacy_id = fields.Integer(string='ID de origen', readonly=True, index=True)

    _sql_constraints = [
        ('legacy_uniq', 'unique(legacy_model, legacy_id)',
         'Ya existe un registro migrado desde ese origen.'),
    ]

    # ------------------------------------------------------------------
    # Cálculos
    # ------------------------------------------------------------------

    @api.depends('tipo_registro_id', 'date', 'partner_id')
    def _compute_name(self):
        for rec in self:
            tpl = rec.tipo_registro_id.name_template
            if tpl:
                rec.name = plantilla.render(rec, tpl)
                continue
            # Un Char vacío en Odoo vale False, no '': hay que filtrarlos o el
            # join revienta con un contacto o un tipo sin nombre.
            partes = [
                rec.tipo_registro_id.name,
                rec.date.strftime('%d/%m/%Y') if rec.date else None,
                rec.partner_id.name,
            ]
            rec.name = ' - '.join(p for p in partes if p) or ''

    @api.depends('marca_bijou')
    def _compute_marca_bijou_url(self):
        for rec in self:
            rec.marca_bijou_url = MARCA_BIJOU_URLS.get(rec.marca_bijou, False)

    def action_abrir_marca_bijou(self):
        self.ensure_one()
        if self.marca_bijou_url:
            return {'type': 'ir.actions.act_url', 'url': self.marca_bijou_url,
                    'target': 'new'}
        return True

    def action_descargar_imagen(self):
        """Descarga el archivo de la imagen, no sólo la vista previa.

        widget="image" sólo permite ampliarla o reemplazarla; no hay forma de
        bajarla desde ahí. La ruta /web/content con download=true es la misma
        que usa el widget="binary" estándar de Odoo para su icono de descarga.
        """
        self.ensure_one()
        if not self.imagen:
            return True
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/%d/imagen?download=true' % (self._name, self.id),
            'target': 'self',
        }

    @api.depends('fecha_renovacion')
    def _compute_alerta_renovacion(self):
        hoy = fields.Date.context_today(self)
        for rec in self:
            if rec.fecha_renovacion:
                meses = ((rec.fecha_renovacion.year - hoy.year) * 12
                         + rec.fecha_renovacion.month - hoy.month)
                rec.alerta_renovacion = meses <= 3
            else:
                rec.alerta_renovacion = False

    # ------------------------------------------------------------------
    # Catálogo de campos dinámicos
    # ------------------------------------------------------------------

    @api.model
    @tools.ormcache('tipo_id')
    def _arsante_catalogo(self, tipo_id):
        """Campos dinámicos de un tipo, como tuplas inmutables (van a ormcache).

        tipo_id None -> todos los tipos activos, agrupados, para el modo B.
        """
        dominio = [('active', '=', True)]
        if tipo_id:
            dominio.append(('tipo_registro_id', '=', tipo_id))
        campos = self.env['arsante.campo'].sudo().search(
            dominio, order='tipo_registro_id, sequence, id')
        return tuple(
            (c.tipo_registro_id.id, c.field_name, c.name, c.ttype, c.seccion,
             c.requerido, c.solo_lectura, c.ayuda or '', c.placeholder or '',
             c.widget or '', c.comodel_domain or '', c.mostrar_en_lista,
             c.mostrar_en_busqueda, c.agrupable, c.mostrar_en_formulario,
             c.es_nucleo)
            for c in campos
            if c.field_name in self._fields
        )

    # ------------------------------------------------------------------
    # Inyección en las vistas
    # ------------------------------------------------------------------

    @api.model
    def _get_view_cache_key(self, view_id=None, view_type='form', **options):
        """Añade el tipo de registro a la clave de caché de vistas.

        La clave debe ser 'arsante_tipo_registro_id' y no 'default_...': el
        viewService del cliente descarta las claves default_* al construir su
        propia clave de caché (web/static/src/views/view_service.js), con lo que
        el navegador serviría la vista de otro tipo.
        """
        clave = super()._get_view_cache_key(view_id, view_type, **options)
        return clave + (self.env.context.get('arsante_tipo_registro_id'),)

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type in ('form', 'tree', 'search'):
            try:
                self._arsante_inyectar(arch, view_type)
            except Exception:
                # Un catálogo mal formado no puede dejar el módulo inaccesible:
                # se sirve la vista base y se registra el fallo.
                _logger.exception(
                    "arsante: fallo inyectando campos dinámicos en la vista %s",
                    view_type)
        return arch, view

    def _arsante_inyectar(self, arch, view_type):
        # Idempotencia: si otro override ya encadenó una inyección, se rehace.
        for nodo in arch.xpath('//*[@%s]' % MARCA):
            nodo.getparent().remove(nodo)

        tipo_id = self.env.context.get('arsante_tipo_registro_id')
        if tipo_id:
            tipo_id = int(tipo_id)
        catalogo = self._arsante_catalogo(tipo_id)
        if not catalogo:
            return

        if view_type == 'form':
            self._inyectar_form(arch, catalogo, tipo_id)
        elif view_type == 'tree' and tipo_id:
            # Sin tipo concreto habría que meter todas las columnas de todos los
            # tipos: ilegible y caro. La lista se queda con los campos comunes.
            self._inyectar_tree(arch, catalogo)
        elif view_type == 'search':
            self._inyectar_search(arch, catalogo)

    def _inyectar_form(self, arch, catalogo, tipo_id):
        # Los campos marcados como "no mostrar en el formulario" siguen
        # existiendo y se pueden filtrar, agrupar y exportar; sólo se ocultan
        # aquí. Se aplica igual a los estándar (es_nucleo) que a los propios de
        # cada tipo: sólo tipo_registro_id e imagen quedan fuera de este
        # catálogo por completo, fijos en la vista estática.
        catalogo = tuple(d for d in catalogo if d[14])
        if not catalogo:
            return

        if tipo_id:
            # Modo A: un solo tipo, los campos van directos a sus anclas.
            for seccion, ancla in ANCLAS_FORM.items():
                destino = arch.xpath("//*[@name='%s']" % ancla)
                if not destino:
                    continue
                for datos in catalogo:
                    if datos[4] == seccion:
                        for nodo in self._nodos_form(datos):
                            destino[0].append(nodo)
            return

        # Modo B: sin tipo en contexto (Todos los Registros, enlace directo).
        # Un grupo por tipo, visible sólo cuando el registro es de ese tipo.
        destino = arch.xpath("//*[@name='%s']" % ANCLAS_FORM['izq'])
        if not destino:
            return
        destino = destino[0]
        self._asegurar_campo_invisible(arch, 'tipo_registro_id')

        por_tipo = {}
        for datos in catalogo:
            por_tipo.setdefault(datos[0], []).append(datos)

        Tipo = self.env['arsante.tipo_registro'].sudo()
        for tid, campos in por_tipo.items():
            grupo = etree.Element('group')
            grupo.set(MARCA, '1')
            grupo.set('string', Tipo.browse(tid).name or '')
            grupo.set('attrs', str({'invisible': [('tipo_registro_id', '!=', tid)]}))
            for datos in campos:
                for nodo in self._nodos_form(datos):
                    grupo.append(nodo)
            destino.addnext(grupo)

    def _nodos_form(self, datos):
        """Nodos a insertar en el form para un campo del catálogo.

        Normalmente uno solo (el <field>). Algunos campos (marca_bijou) llevan
        además un botón condicionado a otro campo, y eso necesita su propia
        pareja <label>+fila: meter dos <field> sueltos seguidos en un <group>
        rompe el emparejamiento automático etiqueta/valor de todo lo que venga
        después (ya nos pasó una vez con los campos de ISP).
        """
        field_name = datos[1]
        config_boton = CAMPOS_CON_BOTON.get(field_name)
        if not config_boton:
            return [self._nodo_field(datos, 'form')]
        return self._nodos_campo_con_boton(datos, config_boton)

    def _nodos_campo_con_boton(self, datos, config):
        (_tid, field_name, etiqueta, _ttype, _seccion, requerido, solo_lectura,
         ayuda, _placeholder, _widget, _dominio, _lista, _busq, _agr,
         _form, _nucleo) = datos

        label = etree.Element('label')
        label.set('for', field_name)
        label.set('string', etiqueta)
        label.set(MARCA, '1')

        fila = etree.Element('div')
        fila.set('class', 'o_row')
        fila.set(MARCA, '1')

        campo = etree.SubElement(fila, 'field')
        campo.set('name', field_name)
        campo.set('class', 'oe_inline')
        campo.set('nolabel', '1')
        if ayuda:
            campo.set('help', ayuda)
        attrs = {}
        if requerido:
            attrs['required'] = [(1, '=', 1)]
        if solo_lectura:
            attrs['readonly'] = [(1, '=', 1)]
        if attrs:
            campo.set('attrs', str(attrs))

        boton = etree.SubElement(fila, 'button')
        boton.set('name', config['metodo'])
        boton.set('string', config['boton_string'])
        boton.set('type', 'object')
        boton.set('icon', config['icono'])
        boton.set('class', 'oe_link')
        boton.set('attrs', str({'invisible': [(config['campo_url'], '=', False)]}))

        return [label, fila]

    def _inyectar_tree(self, arch, catalogo):
        raiz = arch if arch.tag == 'tree' else None
        if raiz is None:
            encontrado = arch.xpath('//tree')
            if not encontrado:
                return
            raiz = encontrado[0]
        for datos in catalogo:
            if datos[11]:  # mostrar_en_lista
                raiz.append(self._nodo_field(datos, 'tree'))

    def _inyectar_search(self, arch, catalogo):
        raiz = arch if arch.tag == 'search' else None
        if raiz is None:
            encontrado = arch.xpath('//search')
            if not encontrado:
                return
            raiz = encontrado[0]

        for datos in catalogo:
            if datos[12]:  # mostrar_en_busqueda
                campo = etree.Element('field')
                campo.set('name', datos[1])
                campo.set('string', datos[2])
                campo.set(MARCA, '1')
                raiz.insert(0, campo)

        grupo = arch.xpath("//group[@name='arsante_group_by']")
        if not grupo:
            return
        for datos in catalogo:
            if datos[13]:  # agrupable
                filtro = etree.Element('filter')
                filtro.set('name', 'gb_%s' % datos[1])
                filtro.set('string', datos[2])
                filtro.set('domain', '[]')
                filtro.set('context', "{'group_by': '%s'}" % datos[1])
                filtro.set(MARCA, '1')
                grupo[0].append(filtro)

    def _nodo_field(self, datos, view_type):
        """Construye el <field>. Siempre con etree, nunca concatenando texto:
        las etiquetas las escribe el usuario y podrían inyectar XML."""
        (_tid, field_name, etiqueta, ttype, _seccion, requerido, solo_lectura,
         ayuda, placeholder, widget, dominio, _lista, _busq, _agr,
         _form, _nucleo) = datos

        nodo = etree.Element('field')
        nodo.set('name', field_name)
        nodo.set('string', etiqueta)
        nodo.set(MARCA, '1')

        if widget:
            nodo.set('widget', widget)
        if ayuda:
            nodo.set('help', ayuda)
        if placeholder:
            nodo.set('placeholder', placeholder)
        if dominio and dominio != '[]':
            nodo.set('domain', dominio)

        if view_type == 'tree':
            nodo.set('optional', 'show')
            return nodo

        # required en la vista, nunca NOT NULL en la columna: la columna es común
        # a todos los tipos y los registros históricos pueden no tener el dato.
        attrs = {}
        if requerido:
            attrs['required'] = [(1, '=', 1)]
        if solo_lectura:
            attrs['readonly'] = [(1, '=', 1)]
        if attrs:
            nodo.set('attrs', str(attrs))
        return nodo

    def _asegurar_campo_invisible(self, arch, nombre):
        """El campo debe estar en la vista para que los attrs lo puedan evaluar."""
        if arch.xpath("//field[@name='%s']" % nombre):
            return
        nodo = etree.Element('field')
        nodo.set('name', nombre)
        nodo.set('invisible', '1')
        nodo.set(MARCA, '1')
        raiz = arch.xpath('//sheet') or arch.xpath('//form') or [arch]
        raiz[0].insert(0, nodo)

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def action_archivar(self):
        self.write({'active': False})

    def action_desarchivar(self):
        self.write({'active': True})

    def action_create_so(self):
        """Crea una nota de venta con una línea por registro seleccionado.

        Sustituye a los 20 métodos create_so() distintos: el texto de cada línea
        sale ahora de la plantilla configurada en el tipo de registro.

        Se usa ``self`` directamente, no ``context['active_ids']``: ese patrón
        venía del código legacy, pensado para acciones de servidor sin
        recordset propio. Aquí el método se llama desde dos sitios y ambos YA
        traen el recordset correcto — el botón del formulario (``self`` es el
        registro abierto) y la acción de la lista (Odoo puebla ``records`` con
        los seleccionados antes de ejecutar el código). Leer ``active_ids`` del
        contexto podía arrastrar una selección obsoleta de otra pantalla y
        operar sobre el registro equivocado.
        """
        registros = self
        if not registros:
            raise UserError(_("No hay registros seleccionados."))

        if registros.filtered('sale_order_id'):
            raise ValidationError(
                _("Algunos registros ya tienen asociada una nota de venta!"))
        if len(registros.tipo_registro_id) > 1:
            raise ValidationError(
                _("No puede mezclar tipos de registro en una nota de venta!"))
        if len(registros.partner_id) > 1:
            raise ValidationError(
                _("No puede tener clientes distintos para crear una nota de venta!"))
        if not registros.partner_id:
            raise ValidationError(_("Los registros no tienen cliente asignado."))

        tipo = registros.tipo_registro_id
        registros._check_campos_so(tipo)

        orden = self.env['sale.order'].create({
            'name': self.env['ir.sequence'].next_by_code('sale.order') or _('New'),
            'date_order': fields.Datetime.now(),
            'partner_id': registros[0].partner_id.id,
            'tipo_registro_id': tipo.id,
            'marca': (plantilla.valor_str(registros[0], tipo.so_marca_code)
                      if tipo.so_marca_code else False),
        })

        for rec in registros:
            producto = rec._resolver_producto(tipo)
            self.env['sale.order.line'].create({
                'name': plantilla.render(rec, tipo.so_line_template) or rec.display_name,
                'product_id': producto.id,
                'product_uom_qty': 1,
                'product_uom': producto.uom_id.id,
                'order_id': orden.id,
            })
            rec.sale_order_id = orden.id

        if tipo.so_dte_referencia:
            registros._crear_referencia_dte(orden, tipo)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': orden.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _check_campos_so(self, tipo):
        """Valida los campos que el tipo declara obligatorios para facturar.

        Se comprueba aquí y no con un @api.constrains porque los 1.926 registros
        históricos ya facturados pueden estar incompletos: un constraint genérico
        impediría reabrirlos o modificarlos.
        """
        codigos = [c.strip() for c in (tipo.so_required_codes or '').split(',') if c.strip()]
        if not codigos:
            return
        etiquetas = {c.code: c.name for c in tipo.campo_ids}
        faltantes = {}
        for rec in self:
            faltan = [etiquetas.get(c, c) for c in codigos
                      if not plantilla.valor_bruto(rec, c)]
            if faltan:
                faltantes[rec.display_name or _('(sin nombre)')] = faltan
        if faltantes:
            detalle = "\n".join(" - %s: %s" % (nombre, ", ".join(campos))
                                for nombre, campos in faltantes.items())
            raise ValidationError(
                _("A algunos registros les falta información obligatoria:\n\n%s",
                  detalle))

    def _resolver_producto(self, tipo):
        self.ensure_one()
        codigo = tipo.so_product_code or 'product_id'
        producto = plantilla.valor_bruto(self, codigo)
        if not producto:
            raise ValidationError(
                _("El registro «%s» no tiene producto asignado.", self.display_name))
        return producto

    def _crear_referencia_dte(self, orden, tipo):
        """Referencia DTE 'Orden de Compra' (l10n_cl_fe).

        l10n_cl_fe no está declarado en depends para no forzar la localización
        chilena en bases de prueba, así que se comprueba en tiempo de ejecución.
        """
        DocClass = self.env.get('sii.document_class')
        if DocClass is None or 'referencia_ids' not in orden._fields:
            _logger.info(
                "arsante: l10n_cl_fe no disponible, se omite la referencia DTE")
            return
        doc = DocClass.sudo().search([('name', '=', 'Orden de Compra')], limit=1)
        if not doc:
            return
        codigos = [c.strip() for c in (tipo.so_oc_codes or '').split(',') if c.strip()]
        folio = next((v for rec in self for c in codigos
                      if (v := plantilla.valor_str(rec, c))), False)
        if folio:
            orden.write({'referencia_ids': [(0, 0, {
                'fecha_documento': fields.Date.context_today(self),
                'folio': folio,
                'sii_referencia_TpoDocRef': doc.id,
            })]})
