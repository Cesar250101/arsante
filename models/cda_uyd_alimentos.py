# -*- coding: utf-8 -*-

from calendar import month
from cmath import e
from datetime import datetime
from odoo.exceptions import Warning
from odoo import models, fields, api, exceptions, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

class CdaCosmetico(models.Model):
    _name = 'arsante.cda_uyd_alimentos'

    def _default_get(self):
        tipo_id=self.env['arsante.tipo_registro'].search([('tipo','=','cda_uyd_alimentos')])
        return tipo_id

    tipo_registro_id = fields.Many2one(
        comodel_name='arsante.tipo_registro',
        string='Tipo de Registro',
        required=True, default=_default_get,readonly=True,store=True)
    name = fields.Char(string='Nombre Registro')
    date = fields.Date(string='Fecha Registro')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Cliente')
    va_cesmec=fields.Boolean(string="Va a Cesmec?")
    au = fields.Char(string='AU')
    nro_cda = fields.Char(string='Nº CDA')
    item = fields.Char(string='Item')
    agente_aduana_id = fields.Many2one(comodel_name='res.partner', string='Agente Aduana')
    ref_tramite = fields.Char(string='Ref. Trámite')
    proveedor_id = fields.Many2one(comodel_name='res.partner', string='Proveedor')
    marca = fields.Selection([
        ('todomoda', 'Todo Moda'),
        ('isadora', 'Isadora'),
    ], string='Marca')
    cda_marca_url = fields.Char(string='URL OneDrive', compute='_compute_cda_marca_url')
    fecha_llegada = fields.Date(string='Fecha Llegada')
    enviar_colilla = fields.Boolean(string='Envíar Colilla?')
    enviar_colilla_fecha = fields.Date(string='Fecha envíar colilla')
    subir_cloud = fields.Boolean(string='Subir Cloud?')
    enviar_subir = fields.Boolean(string='Enviar y Subir UYD?')
    enviar_cda = fields.Boolean(string='Envíar CDA?')
    subir_drive = fields.Boolean(string='Subir Drive?')
    # enviar_uyd = fields.Boolean(string='Envíar UYD?')
    exim_ctrl_calidad = fields.Char(string='Exim. Cntrl Calidad')
    sale_order_id = fields.Many2one(comodel_name='sale.order', string='Nota de Venta')
    facturado = fields.Boolean(string='Facturado?')
    nro_resolucion=fields.Char(string='Nro. Resolución')
    pdf_nro_resolucion = fields.Binary('PDF Resolucion')
    product_id = fields.Many2one(comodel_name='product.product', string='Producto')
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
        ids = self.env["arsante.cda_uyd_alimentos"].browse(self._context.get("active_ids", []))

        sale_order_line_ids=[]
        now = datetime.now()
        sale_order_id=False
        for i in ids:
            if i.sale_order_id:
                raise ValidationError("Algunos registros ya tienen asociada una nota de venta!")
        for i in ids:
            if i.nro_cda and i.proveedor_id and i.cda_marca_id:
                if not sale_order_id:
                    value={
                        'name':self.env['ir.sequence'].next_by_code('sale.order') or _('New'),
                        'date_order':now,
                        'partner_id':i.partner_id.id,
                        "tipo_registro_id":self.tipo_registro_id.id,
                    }
                    partner_id_1=i.partner_id.id
                    sale_order_id=model_sale_order.create(value)
                Value={
                    'name':' Nº CDA: '+i.nro_cda+' ITEM: '+str(i.item)+' PROVEEDOR: '+i.proveedor_id.name+' MARCA:'+i.cda_marca_id.name,
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
                              -AU
                              -Nº CDA
                              -Item
                              -Proveedor
                              -Marca
                              """)
        # rec.write({
        #     'order_line':[(6, 0, [sale_order_line_ids])]
        # })

    @api.depends('estado','no_cotizado','documentacion','facturado','fecha_renovacion','requiere_renovacion')
    def _compute_alerta_renovacion(self):
        for i in self:
            if i.fecha_renovacion:
                diferencia_meses = (i.fecha_renovacion.year - datetime.now().year) * 12 + (i.fecha_renovacion.month - datetime.now().month)
                if diferencia_meses <=3:
                    i.alerta_renovacion = True
                else:
                    i.alerta_renovacion = False

    def write(self, vals):
        rec= super(CdaCosmetico,self).write(vals)
        try:
            descripcion_venta='Gicona:'+self.referencia_gicona if self.referencia_gicona else ''
            descripcion_venta+=' ISP:'+self.nro_isp if self.nro_isp else ''
            descripcion_venta+=' Fabricante:'+self.fabricante_id.name if self.fabricante_id else ''
            descripcion_venta+=' Nº Resolución:'+self.nro_resolucion if self.nro_resolucion else ''
            if self.product_id.marcar_id:
                descripcion_venta+=' Marca:'+self.product_id.marca_id.name if self.product_id else ''
            
        except:
            descripcion_venta=False
            pass
        if descripcion_venta:
            values={
                'description_sale':descripcion_venta 
            }
            self.product_id.write(values)        
        return rec
    
    @api.model_create_multi
    def create(self, vals):
        rec= super(CdaCosmetico,self).create(vals)
        try:
            fabricante=self.env['res.partner'].browse(vals[0]['fabricante_id'])
            descripcion_venta='Gicona:'+vals[0]['referencia_gicona'] if vals[0]['referencia_gicona'] else ''
            descripcion_venta+=' ISP:'+vals[0]['nro_isp'] if vals[0]['nro_isp'] else ''
            descripcion_venta+=' Fabricante:'+fabricante.name if fabricante else ''
            descripcion_venta+=' Nº Resolución:'+vals[0]['nro_resolucion'] if vals[0]['nro_resolucion'] else ''
            if rec.product_id.marcar_id:
                descripcion_venta+=' Marca:'+rec.product_id.marca_id.name if rec.product_id else ''

        except:
            descripcion_venta=False
            pass
        if descripcion_venta:
            values={
                'description_sale':descripcion_venta 
            }
            rec.product_id.write(values)
        
        return rec

    @api.depends('marca')
    def _compute_cda_marca_url(self):
        """Asigna automáticamente el link de SharePoint según la marca seleccionada"""
        for record in self:
            if record.marca == 'todomoda':
                record.cda_marca_url = 'https://arsanteconsultores-my.sharepoint.com/personal/pmuquillaza_arsante_cl/_layouts/15/onedrive.aspx?id=%2Fpersonal%2Fpmuquillaza%5Farsante%5Fcl%2FDocuments%2F1%2E%20CLIENTES%20VIGENTES%20AR%20SANTE%202025%2F0%2E%20COLILLAS%20DE%20PAGO%20BIJOU%2FBIJOU%2F2%2E%20colillas%20de%20pago%20TODO%20MODA&ga=1'
            elif record.marca == 'isadora':
                record.cda_marca_url = 'https://arsanteconsultores-my.sharepoint.com/personal/pmuquillaza_arsante_cl/_layouts/15/onedrive.aspx?id=%2Fpersonal%2Fpmuquillaza%5Farsante%5Fcl%2FDocuments%2F1%2E%20CLIENTES%20VIGENTES%20AR%20SANTE%202025%2F0%2E%20COLILLAS%20DE%20PAGO%20BIJOU%2FBIJOU%2F1%2E%20colillas%20de%20pago%20ISADORA&ga=1'
            else:
                record.cda_marca_url = False
    def open_cda_marca_link(self):
        """Abre el enlace del campo cda_marca_url si está disponible"""
        self.ensure_one()
        if self.cda_marca_url:
            url = self.cda_marca_url if self.cda_marca_url.startswith('http') else 'https://' + self.cda_marca_url
            return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'new',
            }
        return True

    def get_invoice_ids(self):
        ids_grabar=[]
        for i in self.sale_id.invoice_ids:
                self.write({
                    'invoice_ids':[(4,0,i.id)]
                })