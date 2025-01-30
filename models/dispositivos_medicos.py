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
    _name = 'arsante.dispositivos_medicos'

    name = fields.Char(string='Nombre Registro')
    def _default_get(self):
        tipo_id=self.env['arsante.tipo_registro'].search([('tipo','=','dispositivos_medicos')])
        return tipo_id

    tipo_registro_id = fields.Many2one(
        comodel_name='arsante.tipo_registro',
        string='Tipo de Registro',
        required=True, default=_default_get,readonly=True,store=True)
    date = fields.Date(string='Fecha Registro')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Cliente')
    categoria = fields.Selection([
        ('declaraciones', 'Declaraciones'),
        ('inscripción_empresa', 'Inscripción Empresa'),
        ('dec_sit_reg_dm', 'Decl situación regul. de DM'),
        ('rev_ant_dm', 'Revisión antecedentes que acompañan DM'),
    ], string='Categoría')
    ref_isp = fields.Char(string='Ref. ISP')
    nro_registro = fields.Char(string='Nro. Registro')
    product_id = fields.Many2one(comodel_name='product.product', string='Producto')
    fabricante_id = fields.Many2one(comodel_name='res.partner', string='Fabricante')
    fecha_ingreso = fields.Date(string='Fecha Ingreso')
    nro_resolucion=fields.Char(string='Nro. Resolución')
    estado = fields.Char(string='Estado')
    comentario = fields.Text(string='Comentario')
    fecha_resolucion = fields.Date(string='Fecha Resolución')
    fecha_ult_renovacion = fields.Date(string='Fecha últ. renovación')
    fecha_vcto = fields.Date(string='Fecha Vencimiento')
    sale_order_id = fields.Many2one(comodel_name='sale.order', string='Nota de Venta')

    enviar_colilla = fields.Boolean(string='Envíar Colilla')
    enviar_cliente = fields.Boolean(string='Envíar Cliente')
    facturado = fields.Boolean(string='Facturado')
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
                if diferencia_meses <= 3:
                    i.alerta_renovacion = True
                else:
                    i.alerta_renovacion = False
