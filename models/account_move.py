# -*- coding: utf-8 -*-

from calendar import month
from cmath import e
from datetime import datetime
from odoo.exceptions import Warning
from odoo import models, fields, api, exceptions
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning


class AccountMove(models.Model):
    _inherit = 'account.move'

    es_arsante = fields.Boolean(string='Es Arsante', related='company_id.es_arsante')
    tipo_registro_id = fields.Many2one(comodel_name='arsante.tipo_registro',string='Tipo de Registro' )
    tipo_servicio_id = fields.Many2one(comodel_name='arsante.tipo_servicio',string='Tipo de Servicio' )     
    tipo_serv_registro= fields.Char(string='Tipo Servicio/Registro',compute='_compute_tipo_serv_registro',store=True)

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


    def action_post(self):
        company_context=self.env.context.get('allowed_company_ids')
        company=self.env['res.company'].search([('id','=',company_context[0])])

        super().action_post()
        if company.es_arsante:
            for rec in self:
                if rec.move_type=='out_invoice':
                    sale_order_id=self.env['sale.order'].search([('company_id','=',company.id),
                                                                ('name','=',rec.invoice_origin)
                                                                ],limit=1)
                    if sale_order_id:
                        cda_cosmetico_ids=self.env['arsante.cda_cosmetico_dm'].search([('sale_order_id','=',sale_order_id.id)])
                        rec.facturado('arsante.cda_cosmetico_dm',sale_order_id)
                        rec.facturado('arsante.cda_uyd_alimentos',sale_order_id)
                        rec.facturado('arsante.dispositivos_medicos',sale_order_id)
                        rec.facturado('arsante.exim_proceso_cosmeticos',sale_order_id)
                        rec.facturado('arsante.eximiciones_cosmeticos',sale_order_id)
                        rec.facturado('arsante.hds_hechas',sale_order_id)
                        rec.facturado('arsante.inscripciones',sale_order_id)
                        rec.facturado('arsante.modificacion_cosmeticos',sale_order_id)
                        rec.facturado('arsante.modificaciones_desinfectantes',sale_order_id)
                        rec.facturado('arsante.rectificaciones',sale_order_id)
                        rec.facturado('arsante.registro_cosmetico',sale_order_id)
                        rec.facturado('arsante.registro_desinfectantes',sale_order_id)
                        rec.facturado('arsante.renovaciones_cosmeticos',sale_order_id)
                        rec.facturado('arsante.renovaciones_desinfectantes',sale_order_id)


    def facturado(self,modelo=False,sale_order_id=False):
        record_ids=self.env[modelo].search([('sale_order_id','=',sale_order_id.id)])
        if record_ids:
            for i in record_ids:
                i.facturado=True
