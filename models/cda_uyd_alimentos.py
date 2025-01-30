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
    cda_marca_id = fields.Many2one(comodel_name='arsante.marcas', string='Marca')
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

    @api.multi
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

    def get_invoice_ids(self):
        ids_grabar=[]
        for i in self.sale_id.invoice_ids:
                self.write({
                    'invoice_ids':[(4,0,i.id)]
                })