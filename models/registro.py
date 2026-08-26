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
from markupsafe import Markup

from odoo import _, api, fields, models, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import html_escape

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
    _inherit = ['mail.thread']
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
    assigned_user_id = fields.Many2one(
        comodel_name='res.users', string='Asignado a', index=True,
        ondelete='set null', domain=lambda self: self._domain_usuarios_asignables(),
        help='Se puede asignar a cualquier usuario interno activo de la '
             'compañía actual.')

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

    # Campos técnicos de mail y de auditoría que no representan una modificación
    # funcional del trámite. Todo el resto, incluidos los x_arsante_* creados
    # desde el configurador, queda registrado en el chatter.
    CAMPOS_SIN_AUDITORIA = frozenset({
        'message_follower_ids', 'message_ids', 'message_main_attachment_id',
        'message_partner_ids', 'message_attachment_count', 'message_has_error',
        'message_has_error_counter', 'message_has_sms_error', 'message_needaction',
        'message_needaction_counter', 'message_unread', 'message_unread_counter',
        'activity_ids', 'activity_state', 'activity_user_id', 'activity_type_id',
        'activity_date_deadline', 'name', 'write_date', 'write_uid',
    })

    @api.model
    def _domain_usuarios_asignables(self):
        return [
            ('active', '=', True),
            ('share', '=', False),
            ('company_ids', 'in', [self.env.company.id]),
        ]

    @api.model_create_multi
    def create(self, vals_list):
        registros = super().create(vals_list)
        for registro, vals in zip(registros, vals_list):
            registro._arsante_registrar_creacion(vals)
        return registros

    def write(self, vals):
        campos = self._arsante_campos_auditar(vals)
        asignados_antes = (
            {registro.id: registro.assigned_user_id.id for registro in self}
            if 'assigned_user_id' in vals else {}
        )
        antes = {
            registro.id: {
                nombre: registro._arsante_valor_auditoria(nombre)
                for nombre in campos
            }
            for registro in self
        }
        resultado = super().write(vals)
        for registro in self:
            cambios = []
            for nombre in campos:
                anterior = antes[registro.id][nombre]
                actual = registro._arsante_valor_auditoria(nombre)
                if anterior != actual:
                    cambios.append((registro._fields[nombre].string or nombre,
                                    anterior, actual))
            if cambios:
                registro._arsante_registrar_actualizacion(cambios, vals)
            if ('assigned_user_id' in vals
                    and asignados_antes.get(registro.id)
                    != registro.assigned_user_id.id):
                registro._arsante_notificar_asignacion()
        return resultado

    def unlink(self):
        if not self.env.user.has_group('arsante.group_arsante_administrador'):
            raise AccessError(_(
                'Solo los usuarios del grupo arsante.administrador pueden '
                'eliminar registros.'))
        return super().unlink()

    @api.constrains('assigned_user_id', 'company_id')
    def _check_usuario_asignado(self):
        for registro in self:
            usuario = registro.assigned_user_id.sudo()
            if usuario and (not usuario.active or usuario.share):
                raise ValidationError(_(
                    'El usuario asignado debe ser un usuario interno activo.'))
            if (usuario and registro.company_id
                    and registro.company_id not in usuario.company_ids):
                raise ValidationError(_(
                    'El usuario asignado debe pertenecer a la compañía del '
                    'registro.'))

    @api.model
    def _arsante_campos_auditar(self, vals):
        return [
            nombre for nombre in vals
            if nombre in self._fields and nombre not in self.CAMPOS_SIN_AUDITORIA
        ]

    def _arsante_valor_auditoria(self, nombre):
        self.ensure_one()
        campo = self._fields[nombre]
        valor = self[nombre]
        if campo.type == 'binary':
            return _('Archivo adjunto') if valor else _('Sin valor')
        valor = campo.convert_to_export(valor, self)
        return str(valor) if valor not in (False, None, '') else _('Sin valor')

    def _arsante_registrar_creacion(self, vals):
        campos = self._arsante_campos_auditar(vals)
        detalle = [
            (self._fields[nombre].string or nombre,
             self._arsante_valor_auditoria(nombre))
            for nombre in campos
        ]
        cuerpo = self._arsante_cuerpo_evento(_('Registro creado'), detalle)
        self.with_context(mail_create_nosubscribe=True).message_post(
            body=cuerpo, message_type='comment', subtype_xmlid='mail.mt_note')

    def _arsante_registrar_actualizacion(self, cambios, vals):
        titulo = (_('Registro asignado') if 'assigned_user_id' in vals
                 else _('Registro actualizado'))
        cuerpo = self._arsante_cuerpo_evento(titulo, cambios)
        self.with_context(mail_create_nosubscribe=True).message_post(
            body=cuerpo, message_type='comment', subtype_xmlid='mail.mt_note')

    def _arsante_notificar_asignacion(self):
        """Envía al nuevo responsable una notificación interna de Odoo."""
        self.ensure_one()
        usuario = self.assigned_user_id
        if not usuario or not usuario.partner_id:
            return
        cuerpo = Markup(
            '<p><strong>%s</strong></p><p>%s <strong>%s</strong>.</p>') % (
                html_escape(_('Registro asignado')),
                html_escape(_('Se te ha asignado el registro')),
                html_escape(self.display_name),
            )
        # Si el asignador y el asignado son la misma persona, Odoo descarta
        # al autor de los destinatarios. OdooBot actúa como autor técnico para
        # que la notificación siempre llegue al usuario responsable.
        odoobot = self.env.ref('base.partner_root', raise_if_not_found=False)
        self.with_context(
            mail_create_nosubscribe=True,
            arsante_force_inbox_partner_ids=[usuario.partner_id.id],
        ).message_post(
            body=cuerpo,
            message_type='notification',
            author_id=odoobot.id if odoobot else False,
            partner_ids=[usuario.partner_id.id],
        )

    def _notify_get_recipients(self, message, msg_vals, **kwargs):
        """Fuerza el inbox para avisos internos de asignación Arsante.

        Los usuarios pueden tener configurado que sus notificaciones se
        manejen por correo. Las asignaciones son operativas y deben verse en
        el centro de mensajes de Odoo, por lo que este contexto acotado cambia
        solo esos destinatarios al canal inbox.
        """
        destinatarios = super()._notify_get_recipients(message, msg_vals, **kwargs)
        inbox_partner_ids = set(
            self.env.context.get('arsante_force_inbox_partner_ids', []))
        for destinatario in destinatarios:
            if destinatario['id'] in inbox_partner_ids:
                destinatario['notif'] = 'inbox'
        return destinatarios

    @staticmethod
    def _arsante_cuerpo_evento(titulo, detalles):
        lineas = []
        for detalle in detalles:
            etiqueta = html_escape(detalle[0])
            if len(detalle) == 2:
                lineas.append(Markup('<li><strong>%s:</strong> %s</li>') %
                              (etiqueta, html_escape(detalle[1])))
            else:
                lineas.append(Markup('<li><strong>%s:</strong> %s → %s</li>') %
                              (etiqueta, html_escape(detalle[1]),
                               html_escape(detalle[2])))
        lista = Markup('').join(lineas) if lineas else Markup('')
        return Markup('<p><strong>%s</strong></p>%s') % (
            html_escape(titulo),
            Markup('<ul>%s</ul>') % lista if lista else Markup(''),
        )

    # ------------------------------------------------------------------
    # Cálculos
    # ------------------------------------------------------------------

    @api.depends('tipo_registro_id', 'date', 'partner_id')
    def _compute_name(self):
        for rec in self:
            # El tipo de registro va siempre primero, sin importar si el resto
            # del nombre sale de una plantilla configurada o del valor por
            # defecto: una name_template no tiene por qué acordarse de
            # incluir {tipo_registro_id} y el usuario necesita distinguir el
            # tipo de un vistazo en listas y búsquedas.
            tpl = rec.tipo_registro_id.name_template
            resto = plantilla.render(rec, tpl) if tpl else rec._name_por_defecto()
            partes = [rec.tipo_registro_id.name, resto]
            rec.name = ' - '.join(p for p in partes if p) or ''

    def _campos_obligatorios(self):
        """arsante.campo con requerido=True del tipo de este registro, en el
        orden de «Campos del formulario» (sequence). Fuente única para el
        nombre por defecto, la descripción de la línea de venta y la
        validación antes de facturar: todos usan lo que el formulario ya
        marca con «*», sin duplicar la lista en otro campo de configuración.
        """
        self.ensure_one()
        return self.env['arsante.campo'].sudo().search([
            ('tipo_registro_id', '=', self.tipo_registro_id.id),
            ('requerido', '=', True),
        ], order='sequence, id')

    def _name_por_defecto(self):
        """Resto del nombre cuando el tipo no tiene «Plantilla del nombre»: el
        valor de cada campo obligatorio. El nombre del tipo de registro lo
        antepone _compute_name."""
        self.ensure_one()
        # Un Char vacío en Odoo vale False, no '': hay que filtrarlos o el
        # join revienta con un campo sin dato.
        valores = [plantilla.valor_str(self, c.code)
                   for c in self._campos_obligatorios()]
        return ' - '.join(v for v in valores if v)

    def _descripcion_linea_so(self):
        """Descripción de la línea de venta.

        Si el tipo de registro tiene configurada «Plantilla de la línea de
        venta» (so_line_template), se usa esa plantilla. Si no, se cae al
        comportamiento por defecto: tipo de registro + valor de cada campo
        obligatorio, igual para todos los tipos de trámite."""
        self.ensure_one()
        tpl = self.tipo_registro_id.so_line_template
        if tpl:
            return plantilla.render(self, tpl) or self.display_name
        partes = [self.tipo_registro_id.name, self._name_por_defecto()]
        return ' - '.join(p for p in partes if p) or self.display_name

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
        # Los campos se agregan a SUS anclas izquierda/derecha, no como grupos
        # hermanos. Un grupo hermano es una columna más para el renderer de
        # Odoo y terminaba enviando todos los campos al lado derecho.
        destinos = {
            seccion: (arch.xpath("//*[@name='%s']" % ancla) or [None])[0]
            for seccion, ancla in ANCLAS_FORM.items()
        }
        if destinos['izq'] is None:
            return
        self._asegurar_campo_invisible(arch, 'tipo_registro_id')

        por_tipo = {}
        for datos in catalogo:
            por_tipo.setdefault(datos[0], []).append(datos)

        for tid, campos in por_tipo.items():
            for datos in campos:
                destino = destinos.get(datos[4])
                if destino is None:
                    continue
                invisible = [('tipo_registro_id', '!=', tid)]
                for nodo in self._nodos_form(datos, invisible=invisible):
                    destino.append(nodo)

    def _nodos_form(self, datos, invisible=None):
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
            return [self._nodo_field(datos, 'form', invisible=invisible)]
        return self._nodos_campo_con_boton(
            datos, config_boton, invisible=invisible)

    def _nodos_campo_con_boton(self, datos, config, invisible=None):
        (_tid, field_name, etiqueta, _ttype, _seccion, requerido, solo_lectura,
         ayuda, _placeholder, _widget, _dominio, _lista, _busq, _agr,
         _form, _nucleo) = datos

        label = etree.Element('label')
        label.set('for', field_name)
        label.set('string', etiqueta)
        label.set(MARCA, '1')
        if invisible:
            label.set('attrs', str({'invisible': invisible}))

        fila = etree.Element('div')
        fila.set('class', 'o_row')
        fila.set(MARCA, '1')
        if invisible:
            fila.set('attrs', str({'invisible': invisible}))

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
        if invisible:
            attrs['invisible'] = invisible
        if attrs:
            campo.set('attrs', str(attrs))

        boton = etree.SubElement(fila, 'button')
        boton.set('name', config['metodo'])
        boton.set('string', config['boton_string'])
        boton.set('type', 'object')
        boton.set('icon', config['icono'])
        boton.set('class', 'oe_link')
        ocultar_boton = list(invisible or [])
        ocultar_boton.append((config['campo_url'], '=', False))
        boton.set('attrs', str({'invisible': ocultar_boton}))

        return [label, fila]

    def _inyectar_tree(self, arch, catalogo):
        raiz = arch if arch.tag == 'tree' else None
        if raiz is None:
            encontrado = arch.xpath('//tree')
            if not encontrado:
                return
            raiz = encontrado[0]

        # Los campos núcleo (date, partner_id, product_id...) están fijos en el
        # arch estático de registro.xml para que el formulario los tenga
        # aunque el catálogo esté vacío, pero también son configurables (ubicación
        # y secuencia) desde arsante.tipo_registro. Si se dejan ambas copias,
        # la columna sale duplicada y el orden configurado se ignora porque las
        # fijas nunca se mueven. Se quitan aquí y se reinyectan todas en el
        # orden de "sequence" del catálogo, junto con el resto de columnas.
        nombres_catalogo = {datos[1] for datos in catalogo}
        for nodo in list(raiz):
            if nodo.tag == 'field' and nodo.get('name') in nombres_catalogo:
                raiz.remove(nodo)

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

    def _nodo_field(self, datos, view_type, invisible=None):
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
        if invisible:
            attrs['invisible'] = invisible
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

    def action_abrir_asignacion(self):
        """Abre el asistente para asignar uno o varios registros."""
        if not self._puede_asignar_registro():
            raise AccessError(_(
                'Solo los administradores Arsante o usuarios con permisos de '
                'Ajustes pueden asignar registros.'))
        if not self:
            return False
        if len(self.company_id) != 1 or self.company_id != self.env.company:
            raise ValidationError(_(
                'Seleccione registros que pertenezcan a la compañía actual '
                'para asignarlos en conjunto.'))
        return {
            'name': _('Asignar registros'),
            'type': 'ir.actions.act_window',
            'res_model': 'arsante.registro.asignar',
            'view_mode': 'form',
            'view_id': self.env.ref(
                'arsante.arsante_registro_asignar_form_view').id,
            'target': 'new',
            'context': {
                'default_registro_ids': [(6, 0, self.ids)],
                'default_company_id': self.company_id.id,
            },
        }

    @api.model
    def _puede_asignar_registro(self):
        return (
            self.env.user.has_group('arsante.group_arsante_administrador')
            or self.env.user.has_group('base.group_system')
        )

    def action_create_so(self):
        """Crea una nota de venta con una línea por registro seleccionado.

        Sustituye a los 20 métodos create_so() distintos: el texto de cada línea
        sale ahora del tipo de registro más sus campos obligatorios, igual para
        todos los tipos de trámite (ver _descripcion_linea_so).

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
        registros._check_campos_so()

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
                'name': rec._descripcion_linea_so(),
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

    def _check_campos_so(self):
        """Valida los campos obligatorios del tipo (arsante.campo con
        requerido=True) antes de facturar: son los mismos que el formulario
        marca con «*», así que no hace falta duplicarlos aparte en
        «Campos obligatorios para facturar».

        Se comprueba aquí y no con un @api.constrains porque los 1.926 registros
        históricos ya facturados pueden estar incompletos: un constraint genérico
        impediría reabrirlos o modificarlos.
        """
        faltantes = {}
        for rec in self:
            obligatorios = rec._campos_obligatorios()
            faltan = [c.name for c in obligatorios
                      if not plantilla.valor_bruto(rec, c.code)]
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
