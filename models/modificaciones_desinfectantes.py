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
    _name = 'arsante.modificaciones_desinfectantes'

    def _default_get(self):
        tipo_id=self.env['arsante.tipo_registro'].search([('tipo','=','modificaciones_desinfectantes')])
        return tipo_id

    tipo_registro_id = fields.Many2one(
        comodel_name='arsante.tipo_registro',
        string='Tipo de Registro',
        required=True, default=_default_get,readonly=True,store=True)
    name = fields.Char(string='Nombre Registro')
    date = fields.Date(string='Fecha Registro')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Cliente')
    categoria = fields.Char(string='Categoría')
    ref_isp = fields.Char(string='Ref. ISP')
    nro_registro = fields.Char(string='Nro. Registro')
    product_id = fields.Many2one(comodel_name='product.product', string='Producto')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Fabricante')
    documentacion = fields.Char(string='Documentación')
    nro_resolucion = fields.Char(string='Nro. Resolución')
    comentario = fields.Text(string='comentario')
    sale_order_id = fields.Many2one(comodel_name='sale.order', string='Nota de Venta')

    enviar_colilla = fields.Boolean(string='Envíar Colilla')
    enviar_cliente = fields.Boolean(string='Envíar Cliente')
    facturado = fields.Boolean(string='Facturado?')
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
    imagen = fields.Binary(string='Imagen', attachment=True)

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

    def create_so(self):
        model_sale_order=self.env['sale.order']
        model_sale_order_line=self.env['sale.order.line']
        ids = self.env["arsante.modificaciones_desinfectantes"].browse(self._context.get("active_ids", []))

        sale_order_line_ids=[]
        now = datetime.now()
        sale_order_id=False
        for i in ids:
            if i.sale_order_id:
                raise ValidationError("Algunos registros ya tienen asociada una nota de venta!")
        for i in ids:
            if i.ref_isp and i.nro_registro and i.product_id and i.nro_resolucion:
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
                    'name':'Ref. ISP: '+i.ref_isp+' Nº Registro: '+i.nro_registro+' Nro. Resolución: '+i.nro_resolucion,
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
                              -Ref. ISP
                              -Nº Registro
                              -Nro. Resolución
                              -Producto
                              """)
        # rec.write({
        #     'order_line':[(6, 0, [sale_order_line_ids])]
        # })