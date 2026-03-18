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
    _name = 'arsante.modificacion_cosmeticos'

    def _default_get(self):
        tipo_id=self.env['arsante.tipo_registro'].search([('tipo','=','modificacion_cosmeticos')])
        return tipo_id

    tipo_registro_id = fields.Many2one(
        comodel_name='arsante.tipo_registro',
        string='Tipo de Registro',
        required=True, default=_default_get,readonly=True,store=True)
    name = fields.Char(string='Nombre Registro')
    date = fields.Date(string='Fecha Registro')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Cliente')
    mc_categoria=fields.Selection([
                                    ('ampliacion_alcance', 'Ampliación Alcance'),
                                    ('ampliacion_colorantes', 'Ampliación Colorantes'),
                                    ('ampliacion_estudio_estabilidad', 'Ampliación estudio estabilidad'),
                                    ('ampliacion_isadora', 'Ampliación Isadora'),
                                    ('cambio_formula', 'Cambio de fórmula'),
                                    ('cambio_pais', 'Cambio de páis'),
                                    ('cambio_fabricante', 'Cambio fabricante'),
                                    ('modificacion_envase', 'Modificación Envase'),
                                    ('modificacion_especificaciones', 'Modificación especificaciones'),
                                    ('modificacion_formula', 'Modificación Fórmula'),
            ], string='Categoría')
    oc = fields.Char(string='OC')
    sku = fields.Char(string='SKU')
    mc_ref_gicona = fields.Char(string='Referencia Gicona')
    mc_nro_registro = fields.Char(string='Nº Registro')
    product_id = fields.Many2one(comodel_name='product.product', string='Producto')
    fabricante_id = fields.Many2one(comodel_name='res.partner', string='Fabricante')
    documentacion = fields.Selection([
        ('completa', 'Completa'),
        ('in_completa', 'InCompleta')
    ], string='Documentación')    
    enviar_colilla = fields.Boolean(string='Envíar Colilla?')
    enviar_colilla_fecha = fields.Date(string='Fecha envíar colilla')
    nro_resolucion = fields.Char(string='Nº Resolución')
    pdf_nro_resolucion = fields.Binary('PDF Resolucion')
    eximicion = fields.Selection([
        ('si', 'Sí'),
        ('no', 'No')
    ], string='Realiza Eximición')    
    enviar_cliente = fields.Boolean(string='Envíar al Cliente')
    comentario = fields.Text(string='Comentario')
    sale_order_id = fields.Many2one(comodel_name='sale.order', string='Nota de Venta')
    facturado = fields.Boolean(string='Facturado?')
    Subir_resol_drive = fields.Boolean(string='Subir resol. drive?')
    cotizacion_pendiente = fields.Boolean(string='Cotización Pendiente?')
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

    @api.depends('estado','no_cotizado','documentacion','facturado','fecha_renovacion','requiere_renovacion')
    def _compute_alerta_renovacion(self):
        for i in self:
            if i.fecha_renovacion:
                diferencia_meses = (i.fecha_renovacion.year - datetime.now().year) * 12 + (i.fecha_renovacion.month - datetime.now().month)
                if diferencia_meses <= 3:
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

    def get_invoice_ids(self):
        ids_grabar=[]
        for i in self.sale_id.invoice_ids:
                self.write({
                    'invoice_ids':[(4,0,i.id)]
                })
                         
    def create_so(self):
        model_sale_order=self.env['sale.order']
        model_sale_order_line=self.env['sale.order.line']
        ids = self.env["arsante.modificacion_cosmeticos"].browse(self._context.get("active_ids", []))

        sale_order_line_ids=[]
        now = datetime.now()
        sale_order_id=False
        for i in ids:
            if i.sale_order_id:
                raise ValidationError("Algunos registros ya tienen asociada una nota de venta!")
        for i in ids:
            if i.mc_ref_gicona and i.mc_nro_registro and i.product_id and i.fabricante_id and i.nro_resolucion:
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
                    'name':'NRO.GICONA: '+i.mc_ref_gicona+' NRO.REGISTRO: '+i.mc_nro_registro+' PRODUCTO: '+i.product_id.name+' FABRICANTE: '+i.fabricante_id.name+' NRO.RESOLUCION:'+i.nro_resolucion,
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
                              -NRO.GICONA
                              -NRO.REGISTRO
                              -PRODUCTO
                              -FABRICANTE
                              -NRO.RESOLUCION
                              """)
        # rec.write({
        #     'order_line':[(6, 0, [sale_order_line_ids])]
        # })