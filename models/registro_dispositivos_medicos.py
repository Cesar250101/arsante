# -*- coding: utf-8 -*-

from datetime import datetime
from odoo.exceptions import Warning
from odoo import models, fields, api, exceptions, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

class RegistroDispositivosMedicos(models.Model):
    _name = 'arsante.registro_dispositivos_medicos'

    def _default_get(self):
        tipo_id = self.env['arsante.tipo_registro'].search([('tipo', '=', 'registro_dispositivos_medicos')])
        return tipo_id

    tipo_registro_id = fields.Many2one(
        comodel_name='arsante.tipo_registro',
        string='Tipo de Registro',
        required=True, default=_default_get, readonly=True, store=True)
    name = fields.Char(string='Nombre Registro')
    date = fields.Date(string='Fecha Registro')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Cliente')
    va_cesmec = fields.Boolean(string="Va a Cesmec?")
    au = fields.Char(string='AU')
    nro_uyd = fields.Char(string='Nº UYD')
    item = fields.Char(string='N° Items')
    agente_aduana_id = fields.Many2one(comodel_name='res.partner', string='Agente Aduana')
    ref_tramite = fields.Char(string='Ref. Trámite')
    proveedor_id = fields.Many2one(comodel_name='res.partner', string='Proveedor Ref. SEREMI')
    marca = fields.Selection([
        ('no_aplica', 'No Aplica'),
        ('todomoda', 'Todo Moda'),
        ('isadora', 'Isadora'),
    ], string='Marca')
    marca_url = fields.Char(string='URL OneDrive', compute='_compute_marca_url')
    fecha_llegada = fields.Date(string='Fecha Llegada')
    enviar_colilla = fields.Boolean(string='Envíar Colilla?')
    enviar_colilla_fecha = fields.Date(string='Fecha envíar colilla')
    subir_cloud = fields.Boolean(string='Subir Cloud?')
    enviar_subir = fields.Boolean(string='Enviar y Subir UYD?')
    enviar_cda = fields.Boolean(string='Envíar CDA?')
    subir_drive = fields.Boolean(string='Subir Drive?')
    exim_ctrl_calidad = fields.Char(string='Exim. Cntrl Calidad')
    sale_order_id = fields.Many2one(comodel_name='sale.order', string='Nota de Venta')
    oc_facturacion = fields.Char(string='OC Facturación')
    invoice_ids = fields.Many2many('account.move', string='Facturas', related='sale_order_id.invoice_ids', readonly=True)
    facturado = fields.Boolean(string='Facturado?')
    nro_resolucion = fields.Char(string='Nro. Resolución')
    pdf_nro_resolucion = fields.Binary('PDF Resolucion')
    product_id = fields.Many2one(comodel_name='product.product', string='Producto')
    no_cotizado = fields.Boolean(string='No Cotizado?')
    espera_resolucion = fields.Boolean(string='Espera de resolución?')
    estado = fields.Selection(string='Estado', selection=[('listo', 'Listo'), ('no_listo', 'No Listo')], required=False)
    documentacion = fields.Selection(string='Documentacion', selection=[('completa', 'Completa'), ('incompleta', 'Incompleta')], required=False)
    requiere_renovacion = fields.Boolean(string='Requiere Renovacion?')
    fecha_renovacion = fields.Date(string='Fecha de Renovacion', required=False)
    alerta_renovacion = fields.Boolean(
        string='Alerta Renovacion?',
        required=False,
        compute='_compute_alerta_renovacion',
        store=True)
    importado = fields.Boolean(string='Importado en el general')
    active = fields.Boolean(string='Activo', default=True)
    Bodega_llegada = fields.Char(string='Bodega llegada N° CDA')
    fecha_resolucion_nro = fields.Date(string='Fecha Resolución N°')
    correo_ids = fields.Char(string='Correos Electrónicos', placeholder='correo@correo.cl,correo2@correo.cl')
    comentario = fields.Text(string='Comentario')
    imagen = fields.Binary(string='Imagen', attachment=True)
    nro_oc = fields.Char(string='Nro. OC')
    ref_gicona = fields.Char(string='Ref. Gicona')
    nro_registro = fields.Char(string='Nro. Registro')
    frabrante_id=fields.Many2one(comodel_name='res.partner', string='Fribrante')

    @api.depends('marca')
    def _compute_marca_url(self):
        """Asigna automáticamente el link de SharePoint según la marca seleccionada"""
        for record in self:
            if record.marca == 'todomoda':
                record.marca_url = 'https://arsanteconsultores-my.sharepoint.com/personal/pmuquillaza_arsante_cl/_layouts/15/onedrive.aspx?id=%2Fpersonal%2Fpmuquillaza%5Farsante%5Fcl%2FDocuments%2F1%2E%20CLIENTES%20VIGENTES%20AR%20SANTE%202025%2F0%2E%20COLILLAS%20DE%20PAGO%20BIJOU%2FBIJOU%2F2%2E%20colillas%20de%20pago%20TODO%20MODA&ga=1'
            elif record.marca == 'isadora':
                record.marca_url = 'https://arsanteconsultores-my.sharepoint.com/personal/pmuquillaza_arsante_cl/_layouts/15/onedrive.aspx?id=%2Fpersonal%2Fpmuquillaza%5Farsante%5Fcl%2FDocuments%2F1%2E%20CLIENTES%20VIGENTES%20AR%20SANTE%202025%2F0%2E%20COLILLAS%20DE%20PAGO%20BIJOU%2FBIJOU%2F1%2E%20colillas%20de%20pago%20ISADORA&ga=1'
            else:
                record.marca_url = False

    def open_marca_link(self):
        """Abre el enlace de SharePoint según la marca seleccionada"""
        self.ensure_one()
        if self.marca_url:
            url = self.marca_url if self.marca_url.startswith('http') else 'https://' + self.marca_url
            return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'new',
            }
        return True

    @api.onchange('estado', 'no_cotizado', 'documentacion', 'facturado', 'sale_order_id')
    def _compute_dashboard(self):
        try:
            self.tipo_registro_id._compute_registros()
            record_id = self.ids[0]
            all_record_id = self.env['arsante.all_record'].search([
                ('tipo_registro_id', '=', self.tipo_registro_id.id),
                ('registro_id', '=', record_id)
            ], limit=1)
            if all_record_id:
                all_record_id.facturado = self.facturado
                all_record_id.no_cotizado = self.no_cotizado
                all_record_id.estado = self.estado
                all_record_id.documentacion = self.documentacion
                all_record_id.sale_order_id = self.sale_order_id
        except:
            pass

    def create_so(self):
        model_sale_order = self.env['sale.order']
        model_sale_order_line = self.env['sale.order.line']
        ids = self.env["arsante.registro_dispositivos_medicos"].browse(self._context.get("active_ids", []))

        sale_order_line_ids = []
        now = datetime.now()
        sale_order_id = False
        for i in ids:
            if i.sale_order_id:
                raise ValidationError("Algunos registros ya tienen asociada una nota de venta!")
        for i in ids:
            if i.nro_uyd and i.proveedor_id and i.product_id:
                if not sale_order_id:
                    value = {
                        'name': self.env['ir.sequence'].next_by_code('sale.order') or _('New'),
                        'date_order': now,
                        'partner_id': i.partner_id.id,
                        'tipo_registro_id': self.tipo_registro_id.id,
                    }
                    partner_id_1 = i.partner_id.id
                    sale_order_id = model_sale_order.create(value)
                name_base = ' Nº UYD: ' + i.nro_uyd + ' ITEM: ' + str(i.item) + ' PROVEEDOR: ' + i.proveedor_id.name
                name_marca = ' MARCA:' + i.marca if i.marca else ''
                Value = {
                    'name': name_base + name_marca,
                    'product_id': i.product_id.id,
                    'product_uom_qty': 1,
                    'product_uom': i.product_id.uom_id.id,
                    'order_id': sale_order_id.id
                }
                if partner_id_1 != i.partner_id.id:
                    raise ValidationError("No puede tener clientes distintos para crear una nota de venta!")
                rec = model_sale_order_line.create(Value)
                i.sale_order_id = sale_order_id.id
                sale_order_line_ids.append(rec.id)
            else:
                raise ValidationError("""A algunos registros les falta uno de los siguientes datos:
                              -Nº UYD
                              -Proveedor
                              -Producto
                              """)
        # Crear referencia DTE con OC Facturación
        if sale_order_id:
            oc_value = False
            for i in ids:
                if i.oc_facturacion:
                    oc_value = i.oc_facturacion
                    break
            if oc_value:
                doc_class_oc = self.env['sii.document_class'].search([('name', '=', 'Orden de Compra')], limit=1)
                if doc_class_oc:
                    sale_order_id.write({
                        'referencia_ids': [(0, 0, {
                            'fecha_documento': now.date(),
                            'folio': oc_value,
                            'sii_referencia_TpoDocRef': doc_class_oc.id,
                        })]
                    })

    @api.depends('estado', 'no_cotizado', 'documentacion', 'facturado', 'fecha_renovacion', 'requiere_renovacion')
    def _compute_alerta_renovacion(self):
        for i in self:
            if i.fecha_renovacion:
                diferencia_meses = (i.fecha_renovacion.year - datetime.now().year) * 12 + (i.fecha_renovacion.month - datetime.now().month)
                if diferencia_meses <= 3:
                    i.alerta_renovacion = True
                else:
                    i.alerta_renovacion = False
