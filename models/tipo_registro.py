# -*- coding: utf-8 -*-

import logging
from datetime import timedelta

from odoo import models, fields, api, exceptions, _
from odoo.osv import expression

_logger = logging.getLogger(__name__)

class TipoRegistro(models.Model):
    _name = 'arsante.tipo_registro'

    name = fields.Char(string='Nombre')
    tipo = fields.Selection(
        string='Tipo',
        selection=[('cda_cosmetico', 'CDA Cosmetico'),
                   ('cda_uyd_alimentos', 'CDA UYD Alimentos'),
                   ('uyd_alimentos', 'UYD Alimentos'),
                   ('registro_dispositivos_medicos', 'Registro Dispositivos Médicos'),
                   ('cda_dispositivos_medicos', 'CDA Dispositivos Medicos'),
                   ('dispositivos_medicos', 'Dispositivos Medicos'),
                   ('declaracion_dispositivos_medicos', 'Declaración Dispositivos Médicos'),
                   ('rev_antecedentes_dm', 'Rev. Antecedentes DM'),
                   ('exim_proceso_cosmeticos', 'Exmin. Proceso Cosmetico'),
                   ('eximiciones_cosmeticos', 'Eximiciones Cosmetico'),
                   ('hds_hechas', 'HDS Hechas'),
                   ('inscripciones', 'Inscripciones'),
                   ('inscripciones_cosmeticos', 'Inscripción Cosméticos'),
                   ('modificacion_cosmeticos', 'Modificacion Cosmetico'),
                   ('modificaciones_desinfectantes', 'Modificaciones Defectantes'),
                   ('rectificaciones', 'Rectificaciones'),
                   ('registro_cosmetico', 'Registro Cosmetico'),
                   ('registro_desinfectantes', 'Registro Defectantes'),
                   ('renovaciones_cosmeticas', 'Renovaciones Cosmeticas'),
                   ('renovaciones_desinfectantes', 'Renovaciones Defectantes'),
                   ('revision_oc_cosmeticos', 'Revisión OC Cosméticos'),
                   ],
        required=False, )

    # --- Modelo genérico: definición de campos y plantillas -----------------
    # Sustituyen al patrón de "un modelo Python por tipo de trámite".

    code = fields.Char(
        string='Código',
        help="Identificador estable del tipo de registro. Reemplaza al campo "
             "«Tipo», que quedará obsoleto.")
    grupo_id = fields.Many2one(
        comodel_name='arsante.tipo_registro.grupo', string='Grupo',
        help="Agrupa este tipo con otros en el menú lateral (ej. "
             "«Cosméticos», «Dispositivos Médicos»).")
    campo_ids = fields.One2many(
        comodel_name='arsante.campo', inverse_name='tipo_registro_id',
        string='Campos del formulario',
        help="Campos propios de este tipo de trámite. Se crean como campos "
             "reales, por lo que se pueden filtrar, agrupar y exportar.")
    alerta_ids = fields.One2many(
        comodel_name='arsante.alerta', inverse_name='tipo_registro_id',
        string='Alertas',
        help="Avisos basados en campos de fecha de este tipo de trámite.")
    registro_ids = fields.One2many(
        comodel_name='arsante.registro', inverse_name='tipo_registro_id',
        string='Registros')

    name_template = fields.Char(
        string='Plantilla del nombre',
        help="Cómo se compone el nombre del registro. Use {codigo} para "
             "insertar el valor de un campo. Ej.: {partner_id} - {nro_oc}")
    so_line_template = fields.Text(
        string='Plantilla de la línea de venta',
        help="Texto de la línea en la nota de venta. Use {codigo} para "
             "insertar el valor de un campo.\n"
             "Ej.: Nro. OC: {nro_oc} Fabricante: {fabricante_id}")
    so_required_codes = fields.Char(
        string='Campos obligatorios para facturar',
        help="Códigos separados por comas que deben estar rellenos antes de "
             "crear la nota de venta. Ej.: nro_oc,fabricante_id")
    so_product_code = fields.Char(
        string='Campo del producto', default='product_id',
        help="De qué campo sale el producto de la línea de venta.")
    so_marca_code = fields.Char(
        string='Campo de la marca',
        help="Qué campo alimenta el campo «Marca» de la nota de venta.")
    so_dte_referencia = fields.Boolean(
        string='Crear referencia DTE',
        help="Añade a la nota de venta una referencia de tipo «Orden de "
             "Compra» (requiere la localización chilena).")
    so_oc_codes = fields.Char(
        string='Campos del folio de la OC',
        help="Códigos separados por comas, en orden de preferencia, de los que "
             "se toma el folio. Ej.: oc_facturacion,nro_oc")

    action_id = fields.Many2one(
        comodel_name='ir.actions.act_window', string='Acción',
        readonly=True, copy=False, ondelete='set null')
    menu_id = fields.Many2one(
        comodel_name='ir.ui.menu', string='Menú',
        readonly=True, copy=False, ondelete='set null')

    active = fields.Boolean(string='Activo?',default=True)
    total_record_count = fields.Integer(string='Nro. CDA Cosmeticos',required=False,compute='_compute_registros')
    facturados = fields.Integer(string='Nro. Facturados', required=False, compute='_compute_registros')
    no_facturados = fields.Integer(string='Nro. No Facturados', required=False, compute='_compute_registros')
    cotizados = fields.Integer(string='Nro. Cotizados', required=False, compute='_compute_registros')
    no_cotizados = fields.Integer(string='Nro. No Cotizados', required=False, compute='_compute_registros')
    estado_listos = fields.Integer(string='Nro. Listos', required=False, compute='_compute_registros')
    estado_no_listos = fields.Integer(string='Nro. No Listos', required=False, compute='_compute_registros')
    documentacion_completa = fields.Integer(string='Nro. Doc. Completa', required=False, compute='_compute_registros')
    documentacion_completa_no_completa = fields.Integer(string='Nro. Doc. No Completa', required=False, compute='_compute_registros')
    para_renovar = fields.Integer(string='Para Renovar',required=False,compute='_compute_registros')



    @api.depends('registro_ids.invoice_ids', 'registro_ids.sale_order_id',
                 'registro_ids.estado', 'registro_ids.documentacion',
                 'registro_ids.active', 'alerta_ids.campo_id',
                 'alerta_ids.campo_id.active', 'alerta_ids.campo_id.ttype',
                 'alerta_ids.campo_id.field_name',
                 'alerta_ids.dias_anticipacion')
    def _compute_registros(self):
        """Contadores del dashboard.

        Antes eran 20 bloques identicos de ~30 lineas, uno por trámite, que
        recorrian en Python los One2many completos (2.434 registros en cada
        refresco). Con un solo modelo son seis consultas agregadas.
        """
        Registro = self.env['arsante.registro'].with_context(active_test=False)
        base = [('tipo_registro_id', 'in', self.ids)]

        def contar(extra):
            if not self.ids:
                return {}
            grupos = Registro.read_group(
                base + extra, ['tipo_registro_id'], ['tipo_registro_id'])
            return {g['tipo_registro_id'][0]: g['tipo_registro_id_count']
                    for g in grupos}

        total = contar([])
        # La fuente de verdad de facturación es la relación con las facturas,
        # no el booleano histórico facturado. Este último puede estar
        # desactualizado en migraciones o ante anulaciones de documentos.
        facturados = contar([('invoice_ids', '!=', False)])
        cotizados = contar([('sale_order_id', '!=', False)])
        listos = contar([('estado', '=', 'listo')])
        completa = contar([('documentacion', '=', 'completa')])
        for tipo in self:
            n = total.get(tipo.id, 0)
            tipo.total_record_count = n
            tipo.facturados = facturados.get(tipo.id, 0)
            tipo.no_facturados = n - tipo.facturados
            tipo.cotizados = cotizados.get(tipo.id, 0)
            tipo.no_cotizados = n - tipo.cotizados
            tipo.estado_listos = listos.get(tipo.id, 0)
            tipo.estado_no_listos = n - tipo.estado_listos
            tipo.documentacion_completa = completa.get(tipo.id, 0)
            tipo.documentacion_completa_no_completa = n - tipo.documentacion_completa
            # No se usa el booleano histórico ``alerta_renovacion``: cada
            # tipo define en la pestaña Alertas cuál(es) fecha(s) observar y
            # con cuánta anticipación. Un registro cuenta una sola vez aunque
            # cumpla más de una regla.
            dominio_alerta = tipo._dominio_para_renovar()
            tipo.para_renovar = Registro.search_count(
                [('tipo_registro_id', '=', tipo.id), ('active', '=', True)]
                + dominio_alerta) if dominio_alerta else 0

        return True

    # ------------------------------------------------------------------
    # Modelo genérico: navegación y menús auto-generados
    # ------------------------------------------------------------------

    def action_open_registros(self, dominio_extra=None):
        """Abre los registros de este tipo.

        Sustituye a open_tree_cda_cosmeticos(), que mapeaba a mano cada tipo con
        su modelo y su acción mediante 20 ifs encadenados.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'arsante.registro',
            'view_mode': 'tree,form,pivot',
            # `views` es obligatorio al devolver la acción como diccionario:
            # sólo lo calcula ir.actions.act_window al leerse de la base, y
            # _preprocessAction() del cliente hace action.views.map() sin
            # comprobar si existe. Sin esto el botón «Ver» del dashboard
            # revienta con "Cannot read properties of undefined (reading 'map')".
            'views': [(False, 'tree'), (False, 'form'), (False, 'pivot')],
            'domain': [('tipo_registro_id', '=', self.id)] + (dominio_extra or []),
            'context': {
                'default_tipo_registro_id': self.id,
                # No puede llamarse default_*: el viewService del cliente
                # descarta esas claves al cachear la vista.
                'arsante_tipo_registro_id': self.id,
            },
            'target': 'current',
        }

    def action_open_no_facturados(self):
        return self.action_open_registros([
            '|',
            ('sale_order_id', '=', False),
            ('invoice_ids', '=', False),
        ])

    def action_open_facturados(self):
        return self.action_open_registros([('invoice_ids', '!=', False)])

    def action_open_cotizados(self):
        return self.action_open_registros([('sale_order_id', '!=', False)])

    def action_open_no_cotizados(self):
        return self.action_open_registros([('sale_order_id', '=', False)])

    def action_open_para_renovar(self):
        self.ensure_one()
        dominio_alerta = self._dominio_para_renovar()
        if not dominio_alerta:
            # Un dominio explícitamente vacío evita mostrar registros de un
            # tipo que aún no tenga fechas configuradas para alertar.
            dominio_alerta = [('id', '=', 0)]
        return self.action_open_registros([('active', '=', True)] + dominio_alerta)

    def _dominio_para_renovar(self):
        """Dominio de registros cubiertos por las alertas configuradas.

        La condición de cada regla es ``fecha <= hoy + anticipación``; no se
        establece límite inferior, por lo que una fecha vencida sigue siendo
        una alerta pendiente, igual que en el cron diario. ``expression.OR``
        compone correctamente reglas sobre distintos campos de fecha.
        """
        self.ensure_one()
        hoy = fields.Date.context_today(self)
        Registro = self.env['arsante.registro']
        dominios = []
        for alerta in self.alerta_ids:
            campo = alerta.campo_id
            if (not campo.active or campo.ttype != 'date'
                    or campo.tipo_registro_id != self
                    or campo.field_name not in Registro._fields):
                continue
            limite = hoy + timedelta(days=alerta.dias_anticipacion)
            dominios.append([
                (campo.field_name, '!=', False),
                (campo.field_name, '<=', limite),
            ])
        return expression.OR(dominios) if dominios else []

    def _sync_menu(self):
        """Crea o actualiza la acción y el menú de cada tipo de registro.

        Es lo que permite que crear un tipo desde la interfaz genere su propio
        menú, sin escribir XML ni reiniciar el servidor. Si el tipo tiene
        ``grupo_id``, su menú cuelga de un submenú por grupo (creado aquí
        mismo si hace falta) en vez de ir directo bajo «Tipo de Registros».
        """
        Act = self.env['ir.actions.act_window'].sudo()
        Menu = self.env['ir.ui.menu'].sudo()
        padre = self.env.ref('arsante.arsante_menu_tipo_registros',
                             raise_if_not_found=False)
        if not padre:
            return
        grupo_acceso = self.env.ref('arsante.group_arsante_users',
                                     raise_if_not_found=False)

        padres_por_grupo = self._asegurar_submenus_grupo(Menu, padre)

        for tipo in self:
            vals_act = {
                'name': tipo.name or _('Registros'),
                'res_model': 'arsante.registro',
                'view_mode': 'tree,form,pivot',
                'domain': repr([('tipo_registro_id', '=', tipo.id)]),
                'context': repr({
                    'default_tipo_registro_id': tipo.id,
                    'arsante_tipo_registro_id': tipo.id,
                }),
            }
            if tipo.action_id:
                tipo.action_id.write(vals_act)
            else:
                tipo.action_id = Act.create(vals_act).id

            vals_menu = {
                'name': tipo.name or _('Registros'),
                'parent_id': padres_por_grupo.get(tipo.grupo_id.id, padre.id),
                'action': 'ir.actions.act_window,%d' % tipo.action_id.id,
                'active': tipo.active,
            }
            if grupo_acceso:
                vals_menu['groups_id'] = [(6, 0, [grupo_acceso.id])]
            if tipo.menu_id:
                tipo.menu_id.write(vals_menu)
            else:
                tipo.menu_id = Menu.create(vals_menu).id

    def _asegurar_submenus_grupo(self, Menu, padre):
        """{grupo_id: id del submenú} para los grupos usados en ``self``.

        Crea el submenú la primera vez que un tipo de ese grupo se guarda; las
        veces siguientes reutiliza el que ya está en ``grupo.menu_id``.
        """
        grupos = self.mapped('grupo_id')
        resultado = {}
        for grupo in grupos:
            if not grupo.menu_id:
                grupo.menu_id = Menu.create({
                    'name': grupo.name,
                    'parent_id': padre.id,
                    'sequence': grupo.sequence,
                }).id
            resultado[grupo.id] = grupo.menu_id.id
        return resultado

    @api.model_create_multi
    def create(self, vals_list):
        tipos = super().create(vals_list)
        tipos._sync_menu()
        # Un tipo nuevo nace con sus campos estándar ya configurables.
        tipos._asegurar_campos_nucleo()
        return tipos

    def write(self, vals):
        res = super().write(vals)
        if {'name', 'active', 'grupo_id'} & set(vals):
            self._sync_menu()
        return res

    def unlink(self):
        self.menu_id.sudo().unlink()
        self.action_id.sudo().unlink()
        return super().unlink()

    # Campos estándar que se exponen en la configuración para poder ocultarlos
    # y reubicarlos por tipo. Se dejan fuera:
    #   - tipo_registro_id, name, active, alerta_renovacion, legacy_*: no tiene
    #     sentido que el usuario los toque.
    #   - imagen, sale_order_id, oc_facturacion, comentario: tienen widget o
    #     atributos especiales (avatar en la esquina, visibilidad condicional,
    #     pestaña propia) que el motor de inyección genérico no reproduce, así
    #     que se quedan fijos en la vista en vez de ser configurables.
    CAMPOS_NUCLEO = [
        ('date', 'izq', 10), ('partner_id', 'izq', 20),
        ('product_id', 'izq', 30), ('nro_resolucion', 'izq', 40),
        ('nro_uyd', 'izq', 45),
        ('estado', 'der', 10), ('documentacion', 'der', 20),
        ('facturado', 'der', 30), ('no_cotizado', 'der', 40),
        ('espera_resolucion', 'der', 50), ('requiere_renovacion', 'der', 60),
        ('fecha_renovacion', 'der', 70), ('company_id', 'der', 80),
        ('marca_bijou', 'izq', 50),
    ]

    def _asegurar_campos_nucleo(self):
        """Crea la definición de los campos estándar que aún no la tengan.

        Sin esto el usuario ve en el formulario campos que no aparecen en la
        configuración y no puede hacer nada con ellos. Es idempotente: se puede
        llamar tantas veces como haga falta.
        """
        Campo = self.env['arsante.campo'].sudo()
        Registro = self.env['arsante.registro']
        creados = 0
        for tipo in self:
            existentes = set(Campo.with_context(active_test=False).search(
                [('tipo_registro_id', '=', tipo.id)]).mapped('code'))
            vals_list = []
            for code, seccion, secuencia in self.CAMPOS_NUCLEO:
                if code in existentes or code not in Registro._fields:
                    continue
                campo = Registro._fields[code]
                vals_list.append({
                    'tipo_registro_id': tipo.id,
                    'name': campo.string or code,
                    'code': code,
                    'ttype': campo.type,
                    'comodel_name': (campo.comodel_name
                                     if campo.type == 'many2one'
                                     and campo.comodel_name in dict(
                                         Campo._fields['comodel_name'].selection)
                                     else False),
                    'seccion': seccion,
                    'sequence': secuencia,
                    'es_nucleo': True,
                    'mostrar_en_formulario': True,
                    'mostrar_en_busqueda': True,
                })
            if vals_list:
                Campo.create(vals_list)
                creados += len(vals_list)
        if creados:
            _logger.info("arsante: creadas %d definiciones de campos estándar",
                         creados)
        self.env['arsante.registro'].clear_caches()
        return creados

    def action_crear_campos_nucleo(self):
        self._asegurar_campos_nucleo()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_aplicar_cambios(self):
        """Vacía las cachés y recarga el cliente.

        Cambiar qué campos se muestran no basta con guardarlo: el servidor
        cachea el arch de la vista y el navegador cachea su copia, así que
        hasta recargar se sigue viendo la versión anterior.
        """
        self.env['arsante.registro'].clear_caches()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_regenerar_menu(self):
        """Regenera la acción y el menú de estos tipos (botón del formulario)."""
        self._sync_menu()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_sync_menus(self):
        """Regenera los menús de todos los tipos. Se usa tras la migración."""
        self.search([('active', 'in', (True, False))])._sync_menu()
