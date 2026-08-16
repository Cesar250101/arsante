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
        """Al validar una factura, marca como facturados sus registros arsante.

        Antes eran 14 llamadas hardcodeadas, una por modelo de trámite, que
        había que ampliar a mano con cada tipo nuevo: por eso 8 de los 22 tipos
        no se facturaban. Con un solo modelo basta un write.

        Se corrigen además dos fallos del código anterior: no devolvía el
        resultado de super() y reventaba con IndexError cuando el contexto no
        traía allowed_company_ids (llamadas desde cron o API).
        """
        res = super().action_post()

        facturas = self.filtered(
            lambda m: m.move_type == 'out_invoice'
            and m.invoice_origin
            and m.company_id.es_arsante)
        for factura in facturas:
            orden = self.env['sale.order'].search([
                ('company_id', '=', factura.company_id.id),
                ('name', '=', factura.invoice_origin),
            ], limit=1)
            if not orden:
                continue
            registros = self.env['arsante.registro'].with_context(
                active_test=False).search([
                    ('sale_order_id', '=', orden.id),
                    ('facturado', '=', False),
                ])
            if registros:
                registros.write({'facturado': True})

        return res
