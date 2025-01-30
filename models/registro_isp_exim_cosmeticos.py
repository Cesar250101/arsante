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
    _name = 'arsante.registro_isp_exim_cosmeticos'

    tipo_registro_id = fields.Many2one(
        comodel_name='arsante.tipo_registro',
        string='Tipo de Registro',
        required=True)
    name = fields.Char()
    date = fields.Date(string='Fecha Registro')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Cliente')
    referencia_gicona = fields.Char(string='Referencia Gicona')
    nro_isp = fields.Char(string='Nº ISP')
    pdf_nro_resolucion = fields.Binary('PDF Resolucion')
    product_id = fields.Many2one(comodel_name='product.product', string='Producto Asociado al servicio')
    fabricante_id = fields.Many2one(comodel_name='res.partner', string='Fabricante')
    documentacion = fields.Selection([
        ('completa', 'Completa'),
        ('in_completa', 'InCompleta')
    ], string='Documentación')
    enviar_colilla = fields.Boolean(string='Enviar Colilla')
    nro_resolucion = fields.Char(string='Nº Resolución')
    subir_drive = fields.Boolean(string='Subir Drive')
    sale_id = fields.Many2one(comodel_name='sale.order', string='Cotización')
    invoice_ids = fields.Many2many(comodel_name='account.invoice',string='Facturas')
    comentarios = fields.Text(string='Comentario')
    facturado = fields.Boolean(string='Facturado?')
    cotizacion_pendiente = fields.Boolean(string='Cotización Pendiente?')
    no_cotizado = fields.Boolean(string='No Cotizado?')
    espera_resolucion = fields.Boolean(string='Espera de resolución?')
    estado= fields.Selection(string='Estado',selection=[('listo', 'Listo'),('no_listo', 'No Listo'), ],required=False, )
    documentacion = fields.Selection(string='Documentacion', selection=[('completa', 'Completa'), ('incompleta', 'Incompleta'), ],
                              required=False, )
    fecha_renovacion= fields.Date(
        string='Fecha de Renovacion',
        required=False)

    def write(self, vals):
        rec= super(EximCosmeticos,self).write(vals)
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
        rec= super(EximCosmeticos,self).create(vals)
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
                         
