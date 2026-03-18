# -*- coding: utf-8 -*-

from calendar import month
from cmath import e
from datetime import datetime
from odoo.exceptions import Warning
from odoo import models, fields, api, exceptions, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning


class AllRecord(models.Model):
    _name = 'arsante.all_record'

    tipo_registro_id = fields.Many2one(
        comodel_name='arsante.tipo_registro',
        string='Tipo de Registro',
        required=True, readonly=True,store=True)
    registro_id=fields.Integer(string='ID Registro', required=True)
    name = fields.Char(string='Nombre Registro')
    date = fields.Date(string='Fecha Registro')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Cliente')
    facturado = fields.Boolean(string='Facturado?')
    facturado_int = fields.Integer(string='Cnt. Facturado', compute='_compute_facturado_int', store=True)

    @api.depends('facturado')
    def _compute_facturado_int(self):
        for record in self:
            record.facturado_int = 1 if record.facturado else 0
    no_cotizado = fields.Boolean(string='No Cotizado?')
    estado= fields.Selection(string='Estado',selection=[('listo', 'Listo'),('no_listo', 'No Listo'), ],required=False, )
    documentacion = fields.Selection(string='Documentacion', selection=[('completa', 'Completa'), ('incompleta', 'Incompleta'), ],
                              required=False, )
    sale_order_id = fields.Many2one(comodel_name='sale.order', string='Nota de Venta')

    @api.onchange('facturado','no_cotizado','estado','documentacion')
    def _onchange_facturado(self):
        if self.tipo_registro_id.name=='CDA Cosméticos':
            record_id=self.env['arsante.cda_cosmetico_dm'].search([('id','=',self.registro_id)],limit=1)
        if self.tipo_registro_id.name=='Dispositivos Medicos':
            record_id=self.env['arsante.dispositivos_medicos'].search([('id','=',self.registro_id)],limit=1)
        if self.tipo_registro_id.name=='Eximición Cosméticos':
            record_id=self.env['arsante.eximiciones_cosmeticos'].search([('id','=',self.registro_id)],limit=1)
        if self.tipo_registro_id.name=='Exim. Proceso Cosméticos':
            record_id=self.env['arsante.exim_proceso_cosmeticos'].search([('id','=',self.registro_id)],limit=1)
        if self.tipo_registro_id.name=='HDS Hechas':
            record_id=self.env['arsante.hds_hechas'].search([('id','=',self.registro_id)],limit=1)
        if self.tipo_registro_id.name=='Inscripciones':
            record_id=self.env['arsante.inscripciones'].search([('id','=',self.registro_id)],limit=1)
        if self.tipo_registro_id.name=='Modificacion Cosmeticos':
            record_id=self.env['arsante.modificacion_cosmeticos'].search([('id','=',self.registro_id)],limit=1)
        if self.tipo_registro_id.name=='Modificaciones Desinfectantes':
            record_id=self.env['arsante.modificaciones_desinfectantes'].search([('id','=',self.registro_id)],limit=1)
        if self.tipo_registro_id.name=='Rectificaciones':
            record_id=self.env['arsante.rectificaciones'].search([('id','=',self.registro_id)],limit=1)
        if self.tipo_registro_id.name=='Registro Cosmeticos':
            record_id=self.env['arsante.registro_cosmetico'].search([('id','=',self.registro_id)],limit=1)
        if self.tipo_registro_id.name=='Registro Desinfectantes':
            record_id=self.env['arsante.registro_desinfectantes'].search([('id','=',self.registro_id)],limit=1)
        if self.tipo_registro_id.name=='Renovacion Cosmeticos':
            record_id=self.env['arsante.renovaciones_cosmeticos'].search([('id','=',self.registro_id)],limit=1)
        if self.tipo_registro_id.name=='Renovaciones Desinfectantes':
            record_id=self.env['arsante.renovaciones_cosmeticos'].search([('id','=',self.registro_id)],limit=1)

        record_id.facturado=self.facturado
        record_id.no_cotizado=self.no_cotizado
        record_id.estado=self.estado
        record_id.documentacion=self.documentacion


    def importar_registros(self):
        #CDA Cosmeticos
        self.process_data('arsante.cda_cosmetico_dm')            
        #CDA UYD alimentos
        self.process_data('arsante.cda_uyd_alimentos')            
        #Dispositivos Medicos
        self.process_data('arsante.dispositivos_medicos')
        #arsante.exim_proceso_cosmeticos
        self.process_data('arsante.exim_proceso_cosmeticos')
        #arsante.eximiciones_cosmeticos
        self.process_data('arsante.eximiciones_cosmeticos')
        #arsante.hds_hechas
        self.process_data('arsante.hds_hechas')
        #arsante.inscripciones
        self.process_data('arsante.inscripciones')
        #arsante.modificacion_cosmeticos
        self.process_data('arsante.modificacion_cosmeticos')
        #arsante.modificaciones_desinfectantes
        self.process_data('arsante.modificaciones_desinfectantes')
        #arsante.rectificaciones
        self.process_data('arsante.rectificaciones')
        #arsante.registro_cosmetico
        self.process_data('arsante.registro_cosmetico')
        #arsante.registro_desinfectantes
        self.process_data('arsante.registro_desinfectantes')
        #arsante.renovaciones_cosmeticos
        self.process_data('arsante.renovaciones_cosmeticos')
        #arsante.renovaciones_desinfectantes
        self.process_data('arsante.renovaciones_desinfectantes')




    def process_data(self,modelo=False):
        cda_cosmeticos=self.env[modelo].search([('importado','=',False)])
        if cda_cosmeticos:
            for i in cda_cosmeticos:
                value={
                    'tipo_registro_id':i.tipo_registro_id.id,
                    'registro_id':i.id,
                    'name':i.name,
                    'date':i.date,
                    'partner_id':i.partner_id.id,
                    'facturado':i.facturado,
                    'no_cotizado':i.no_cotizado,
                    'estado':i.estado,
                    'documentacion':i.documentacion,
                    'sale_order_id':i.sale_order_id.id
                }
                i.importado=True
                self.create(value)
