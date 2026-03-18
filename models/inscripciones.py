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
    _name = 'arsante.inscripciones'

    def _default_get(self):
        tipo_id=self.env['arsante.tipo_registro'].search([('tipo','=','inscripciones')])
        return tipo_id

    tipo_registro_id = fields.Many2one(
        comodel_name='arsante.tipo_registro',
        string='Tipo de Registro',
        required=True, default=_default_get,readonly=True,store=True)
    name = fields.Char(string='Nombre Registro')
    date = fields.Date(string='Fecha Registro')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Cliente')
    categoria = fields.Char(string='Categoria')
    ref_gicona = fields.Char(string='Ref. Gicona')
    nro_isp = fields.Char(string='Nro. ISP')
    product_id = fields.Many2one(comodel_name='product.product', string='Producto')
    fabricante_id = fields.Many2one(comodel_name='res.partner', string='Fabricante')
    marca = fields.Char(string='Marca')
    documentacion = fields.Char(string='Documentación')
    enviar_colilla = fields.Boolean(string='Envíar Colilla')
    enviar_colilla_fecha = fields.Date(string='Fecha envíar colilla')
    nro_resolucion = fields.Char(string='Nro. Resolución')
    pdf_nro_resolucion = fields.Binary('PDF Resolucion')
    enviado_cliente = fields.Boolean(string='Enviado a Cliente')
    estado = fields.Selection([
        ('completo', 'Completo'),
        ('incompleto', 'Incompleto'),
    ], string='Estado')
    etiqueta_lista = fields.Selection([
        ('si', 'Sí'),
        ('no', 'No'),
        ('hacer', 'Hacer'),
    ], string='Etiqueta')    
    sale_order_id = fields.Many2one(comodel_name='sale.order', string='Nota de Venta')
    facturado = fields.Boolean(string='Facturado')
    comentario = fields.Text(string='comentario')
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

    def create_so(self):
        model_sale_order=self.env['sale.order']
        model_sale_order_line=self.env['sale.order.line']
        ids = self.env["arsante.inscripciones"].browse(self._context.get("active_ids", []))

        sale_order_line_ids=[]
        now = datetime.now()
        sale_order_id=False
        for i in ids:
            if i.sale_order_id:
                raise ValidationError("Algunos registros ya tienen asociada una nota de venta!")
        for i in ids:
            if i.ref_gicona and i.nro_isp and i.product_id and i.fabricante_id and i.nro_resolucion:
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
                    'name':'Nro.Gicona: '+i.ref_gicona+' Nro.Isp: '+i.nro_isp+' Producto: '+i.product_id.name+' Faricante: '+i.fabricante_id.name+' Nro.Resolución:'+i.nro_resolucion,
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

    @api.depends('estado','no_cotizado','documentacion','facturado','fecha_renovacion','requiere_renovacion')
    def _compute_alerta_renovacion(self):
        for i in self:
            if i.fecha_renovacion:
                diferencia_meses = (i.fecha_renovacion.year - datetime.now().year) * 12 + (i.fecha_renovacion.month - datetime.now().month)
                if diferencia_meses <= 3:
                    i.alerta_renovacion = True
                else:
                    i.alerta_renovacion = False