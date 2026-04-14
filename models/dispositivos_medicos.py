# -*- coding: utf-8 -*-

from calendar import month
from cmath import e
from datetime import datetime
from odoo.exceptions import Warning
from odoo import models, fields, api, exceptions, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

class EximCosmeticos(models.Model):
    _name = 'arsante.dispositivos_medicos'

    name = fields.Char(string='Nombre Registro', compute='_compute_name', store=True)
    @api.depends('tipo_registro_id', 'date', 'partner_id')
    def _compute_name(self):
        for rec in self:
            parts = []
            if rec.tipo_registro_id:
                parts.append(rec.tipo_registro_id.name)
            if rec.date:
                parts.append(rec.date.strftime('%d/%m/%Y'))
            if rec.partner_id:
                parts.append(rec.partner_id.name)
            rec.name = ' - '.join(parts) if parts else ''

    def _default_get(self):
        tipo_id=self.env['arsante.tipo_registro'].search([('tipo','=','dispositivos_medicos')])
        return tipo_id

    tipo_registro_id = fields.Many2one(
        comodel_name='arsante.tipo_registro',
        string='Tipo de Registro',
        required=True, default=_default_get,readonly=True,store=True)
    date = fields.Date(string='Fecha Registro')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Cliente')
    categoria = fields.Selection([
        ('declaraciones', 'Declaraciones'),
        ('inscripción_empresa', 'Inscripción Empresa'),
        ('dec_sit_reg_dm', 'Decl situación regul. de DM'),
        ('rev_ant_dm', 'Revisión antecedentes que acompañan DM'),
    ], string='Categoría')
    marca = fields.Selection([
        ('todomoda', 'Todo Moda'),
        ('isadora', 'Isadora'),
    ], string='Marca')
    marca_url = fields.Char(string='URL OneDrive', compute='_compute_marca_url')
    ref_isp = fields.Char(string='Ref. ISP')
    nro_registro = fields.Char(string='Nro. Registro')
    product_id = fields.Many2one(comodel_name='product.product', string='Producto')
    fabricante_id = fields.Many2one(comodel_name='res.partner', string='Fabricante')
    fecha_ingreso = fields.Date(string='Fecha Llegada')
    nro_resolucion=fields.Char(string='Nro. Resolución')
    estado = fields.Char(string='Estado')
    comentario = fields.Text(string='Comentario')
    fecha_resolucion = fields.Date(string='Fecha Resolución')
    fecha_ult_renovacion = fields.Date(string='Fecha últ. renovación')
    fecha_vcto = fields.Date(string='Fecha Vencimiento')
    sale_order_id = fields.Many2one(comodel_name='sale.order', string='Nota de Venta')
    oc_facturacion = fields.Char(string='OC Facturación')
    invoice_ids = fields.Many2many('account.move', string='Facturas', related='sale_order_id.invoice_ids', readonly=True)

    enviar_colilla = fields.Boolean(string='Envíar Colilla')
    enviar_cliente = fields.Boolean(string='Envíar Cliente')
    facturado = fields.Boolean(string='Facturado')
    no_cotizado = fields.Boolean(string='No Cotizado?')
    espera_resolucion = fields.Boolean(string='Espera de resolución?')
    estado= fields.Selection(string='Estado',selection=[('listo', 'Listo'),('no_listo', 'No Listo'), ],required=False, )
    documentacion = fields.Selection(string='Documentacion', selection=[('completa', 'Completa'), ('incompleta', 'Incompleta'), ],
                              required=False, )
    requiere_renovacion = fields.Boolean(string='Requiere Renovacion?')
    fecha_renovacion= fields.Date(
        string='Fecha de Renovacion',
        required=False)
    alerta_renovacion = fields.Boolean(
        string='Alerta Renovacion?',
        required=False,
        compute='_compute_alerta_renovacion',
        store=True
        )
    importado = fields.Boolean(string='Importado en el general')
    active = fields.Boolean(string='Activo',default=True)
    ref_gicona = fields.Char(string='Ref. Gicona')
    nro_items = fields.Char(string='Nro. Items')
    agente_aduana_id = fields.Many2one(comodel_name='res.partner', string='Agente Aduana')
    nro_cda = fields.Char(string='Nº CDA')
    au = fields.Char(string='N° UYD')
    cc_cesmec= fields.Char(string='CC Cesmec')
    correo_ids = fields.Char(string='Correos Electrónicos', placeholder='correo@correo.cl,correo2@correo.cl')

    @api.onchange('estado','no_cotizado','documentacion','facturado','sale_order_id')
    def _compute_dashboard(self):
        try:
            self.tipo_registro_id._compute_registros()
            record_id=self.ids[0]
            all_record_id=self.env['arsante.all_record'].search([('tipo_registro_id','=',self.tipo_registro_id.id),
                                                                ('registro_id','=',record_id)],limit=1)
            if all_record_id:
                all_record_id.facturado=self.facturado
                all_record_id.no_cotizado=self.no_cotizado
                all_record_id.estado=self.estado
                all_record_id.documentacion=self.documentacion
                all_record_id.sale_order_id=self.sale_order_id
        except:
            pass
        
    def create_so(self):
        model_sale_order=self.env['sale.order']
        model_sale_order_line=self.env['sale.order.line']
        ids = self.env["arsante.dispositivos_medicos"].browse(self._context.get("active_ids", []))

        sale_order_line_ids=[]
        now = datetime.now()
        sale_order_id=False
        for i in ids:
            if i.sale_order_id:
                raise ValidationError("Algunos registros ya tienen asociada una nota de venta!")
        for i in ids:
            if i.ref_isp and i.fabricante_id and i.categoria and i.product_id:
                if not sale_order_id:
                    value={
                        'name':self.env['ir.sequence'].next_by_code('sale.order') or _('New'),
                        'date_order':now,
                        'partner_id':i.partner_id.id,
                        'tipo_registro_id':self.tipo_registro_id.id,
                    }
                    partner_id_1=i.partner_id.id
                    sale_order_id=model_sale_order.create(value)
                Value={
                    'name':'Ref. ISP: '+i.ref_isp+' Fabricante: '+i.fabricante_id.name+' Categoría: '+i.categoria,
                    'product_id':i.product_id.id,
                    'product_uom_qty':1,
                    'product_uom':i.product_id.uom_id.id,
                    'order_id':sale_order_id.id
                }
                if partner_id_1!=i.partner_id.id:
                    raise ValidationError("No puede tener clientes distintos para crear una nota de venta!")

                rec=model_sale_order_line.create(Value)
                i.sale_order_id=sale_order_id.id
                sale_order_line_ids.append(rec.id)

            else:
                raise ValidationError("""A algunos registros les falta uno de los siguierntes datos:
                              -Categori
                              -Ref. ISP
                              -Fabricante
                              -Producto
                              """)
        # rec.write({
        #     'order_line':[(6, 0, [sale_order_line_ids])]
        # })

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

    @api.depends('estado','no_cotizado','documentacion','facturado','fecha_renovacion','requiere_renovacion')
    def _compute_alerta_renovacion(self):
        for i in self:
            if i.fecha_renovacion:
                diferencia_meses = (i.fecha_renovacion.year - datetime.now().year) * 12 + (i.fecha_renovacion.month - datetime.now().month)
                if diferencia_meses <= 3:
                    i.alerta_renovacion = True
                else:
                    i.alerta_renovacion = False
