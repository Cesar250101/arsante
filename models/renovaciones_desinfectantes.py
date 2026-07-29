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
    _name = 'arsante.renovaciones_desinfectantes'

    def _default_get(self):
        tipo_id=self.env['arsante.tipo_registro'].search([('tipo','=','renovaciones_desinfectantes')])
        return tipo_id

    tipo_registro_id = fields.Many2one(
        comodel_name='arsante.tipo_registro',
        string='Tipo de Registro',
        required=True, default=_default_get,readonly=True,store=True)
    name = fields.Char(string='Nombre Registro')
    date = fields.Date(string='Fecha Registro')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Cliente')
    marca = fields.Selection([
        ('no_aplica', 'No Aplica'),
        ('todomoda', 'Todo Moda'),
        ('isadora', 'Isadora'),
    ], string='Marca')
    nro_oc=fields.Char(string='Nº OC')
    ref_SAFIS = fields.Char(string='Ref. SAFIS')
    nro_registro = fields.Char(string='Nº Registro')
    fabricante_id = fields.Many2one(comodel_name='res.partner', string='Fabricante')
    clave_gicona = fields.Char(string='Clave Gicona')
    product_id = fields.Many2one(comodel_name='product.product', string='Nombre ISP Producto')    
    descripcion = fields.Char(string='Descripción')
    reg_insc_isp = fields.Char(string='Nº reg./Insc. ISP')
    estado_renovacion = fields.Char(string='Estado Renovación')
    fecha_vcto = fields.Date(string='Fecha Vcto.')
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
    sale_order_id = fields.Many2one(comodel_name='sale.order', string='Nota de Venta')
    importado = fields.Boolean(string='Importado en el general')
    active = fields.Boolean(string='Activo',default=True)
    imagen = fields.Binary(string='Imagen', attachment=True)
    pdf_resolucion = fields.Binary(string='PDF Resolución', attachment=True)
    nro_resolucion = fields.Char(string='Nº Resolución')
    fecha_resolucion = fields.Date(string='Fecha Resolución')
    correos=fields.Char(string='Correos')
    comentario=fields.Text(string='Comentario')

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
        ids = self.env["arsante.renovaciones_desinfectantes"].browse(self._context.get("active_ids", []))

        sale_order_line_ids=[]
        now = datetime.now()
        sale_order_id=False
        for i in ids:
            if i.sale_order_id:
                raise ValidationError("Algunos registros ya tienen asociada una nota de venta!")
        for i in ids:
            if i.product_id and i.clave_gicona:
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
                    'name':'Nº reg./Insc. ISP: '+i.reg_insc_isp+' Clave Gicona: '+i.clave_gicona,
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
                              -Producto
                              -Nº reg./Insc. ISP
                              -Clave Gicona
                              """)
        # rec.write({
        #     'order_line':[(6, 0, [sale_order_line_ids])]
        # })                    