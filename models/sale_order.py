from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    es_arsante = fields.Boolean(string='Es Arsante', related='company_id.es_arsante')
    fecha_pago = fields.Date(string='Fecha Pago')
    tipo_registro_id = fields.Many2one(comodel_name='arsante.tipo_registro',string='Tipo de Registro' )
    tipo_servicio_id = fields.Many2one(comodel_name='arsante.tipo_servicio',string='Tipo de Servicio' )     
    marca= fields.Char(string='Marca Bijou')
    tipo_serv_registro= fields.Char(string='Tipo Servicio/Registro',
                                    compute='_compute_tipo_serv_registro',  
                                    store=True,readonly=False)

    def _compute_tipo_serv_registro(self):
        """
            Debe hacer los siguente; si el tipo_servicio_id esta vacio debe poner el tipo_registro_id, si el tipo_registro_id esta vacio debe poner el tipo_servicio_id, si ambos tienen valor debe poner "tipo_servicio_id/tipo_registro_id"'
        """
        for order in self:
            if order.tipo_servicio_id and order.tipo_registro_id:
                order.tipo_serv_registro = f"{order.tipo_servicio_id.name}/{order.tipo_registro_id.name}"
            elif order.tipo_servicio_id:
                order.tipo_serv_registro = order.tipo_servicio_id.name
            elif order.tipo_registro_id:
                order.tipo_serv_registro = order.tipo_registro_id.name
            else:
                order.tipo_serv_registro = ''

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        invoice_vals['tipo_registro_id'] = self.tipo_registro_id.id
        invoice_vals['tipo_servicio_id'] = self.tipo_servicio_id.id
        return invoice_vals
    
class TipoServicio(models.Model):
    _name = 'arsante.tipo_servicio'
    _description = 'Tipo de Servicio'

    name = fields.Char(string='Nombre', required=False)      

