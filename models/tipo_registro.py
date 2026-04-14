# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _

class TipoRegistro(models.Model):
    _name = 'arsante.tipo_registro'

    name = fields.Char(string='Nombre')
    tipo = fields.Selection(
        string='Tipo',
        selection=[('cda_cosmetico', 'CDA Cosmetico'),
                   ('cda_uyd_alimentos', 'CDA UYD Alimentos'),
                   ('uyd_alimentos', 'UYD Alimentos'),
                   ('registro_dispositivos_medicos', 'Registro Dispositivos Médicos'),
                   ('cda_dispositivos_medicos', 'CDA Dispositivos Medicos'),
                   ('dispositivos_medicos', 'Dispositivos Medicos'),
                   ('declaracion_dispositivos_medicos', 'Declaración Dispositivos Médicos'),
                   ('exim_proceso_cosmeticos', 'Exmin. Proceso Cosmetico'),
                   ('eximiciones_cosmeticos', 'Eximiciones Cosmetico'),
                   ('hds_hechas', 'HDS Hechas'),
                   ('inscripciones', 'Inscripciones'),
                   ('inscripciones_cosmeticos', 'Inscripción Cosméticos'),
                   ('modificacion_cosmeticos', 'Modificacion Cosmetico'),
                   ('modificaciones_desinfectantes', 'Modificaciones Defectantes'),
                   ('rectificaciones', 'Rectificaciones'),
                   ('registro_cosmetico', 'Registro Cosmetico'),
                   ('registro_desinfectantes', 'Registro Defectantes'),
                   ('renovaciones_cosmeticas', 'Renovaciones Cosmeticas'),
                   ('renovaciones_desinfectantes', 'Renovaciones Defectantes'),
                   ],
        required=False, )

    active = fields.Boolean(string='Activo?',default=True)
    total_record_count = fields.Integer(string='Nro. CDA Cosmeticos',required=False,compute='_compute_registros')
    facturados = fields.Integer(string='Nro. Facturados', required=False, compute='_compute_registros')
    no_facturados = fields.Integer(string='Nro. No Facturados', required=False, compute='_compute_registros')
    cotizados = fields.Integer(string='Nro. Cotizados', required=False, compute='_compute_registros')
    no_cotizados = fields.Integer(string='Nro. No Cotizados', required=False, compute='_compute_registros')
    estado_listos = fields.Integer(string='Nro. Listos', required=False, compute='_compute_registros')
    estado_no_listos = fields.Integer(string='Nro. No Listos', required=False, compute='_compute_registros')
    documentacion_completa = fields.Integer(string='Nro. Doc. Completa', required=False, compute='_compute_registros')
    documentacion_completa_no_completa = fields.Integer(string='Nro. Doc. No Completa', required=False, compute='_compute_registros')
    para_renovar = fields.Integer(string='Para Renovar',required=False,compute='_compute_registros')

    cda_cosmetico_ids = fields.One2many(
        comodel_name='arsante.cda_cosmetico_dm',
        inverse_name='tipo_registro_id',
        string='CDA Cosmeticos',
        required=False)
    cda_uyd_alimentos_ids = fields.One2many(
        comodel_name='arsante.cda_uyd_alimentos',
        inverse_name='tipo_registro_id',
        string='CDA UYD Alimentos',
        required=False)
    uyd_alimentos_ids = fields.One2many(
        comodel_name='arsante.uyd_alimentos',
        inverse_name='tipo_registro_id',
        string='UYD Alimentos',
        required=False)
    dispositivos_medicos_ids = fields.One2many(
        comodel_name='arsante.dispositivos_medicos',
        inverse_name='tipo_registro_id',
        string='Dispositivos Medicos',
        required=False)
    declaracion_dispositivos_medicos_ids = fields.One2many(
        comodel_name='arsante.declaracion_dispositivos_medicos',
        inverse_name='tipo_registro_id',
        string='Declaración Dispositivos Médicos',
        required=False)
    exim_proceso_cosmeticos_ids = fields.One2many(
        comodel_name='arsante.exim_proceso_cosmeticos',
        inverse_name='tipo_registro_id',
        string='Exim. Proceso Cosmeticos',
        required=False)
    eximiciones_cosmeticos_ids = fields.One2many(
        comodel_name='arsante.eximiciones_cosmeticos',
        inverse_name='tipo_registro_id',
        string='Eximiciones Cosmeticos',
        required=False)
    hds_hechas_ids = fields.One2many(
        comodel_name='arsante.hds_hechas',
        inverse_name='tipo_registro_id',
        string='HDS Hechas',
        required=False)
    inscripciones_ids = fields.One2many(
        comodel_name='arsante.inscripciones',
        inverse_name='tipo_registro_id',
        string='Inscripciones',
        required=False)
    inscripciones_cosmeticos_ids = fields.One2many(
        comodel_name='arsante.inscripciones_cosmeticos',
        inverse_name='tipo_registro_id',
        string='Inscripciones Cosméticos',
        required=False)
    modificacion_cosmeticos_ids = fields.One2many(
        comodel_name='arsante.modificacion_cosmeticos',
        inverse_name='tipo_registro_id',
        string='Modificacion Cosmeticos',
        required=False)
    modificaciones_desinfectantes_ids = fields.One2many(
        comodel_name='arsante.modificaciones_desinfectantes',
        inverse_name='tipo_registro_id',
        string='Modificaciones Desinfectantes',
        required=False)
    rectificaciones_ids = fields.One2many(
        comodel_name='arsante.rectificaciones',
        inverse_name='tipo_registro_id',
        string='Rectificaciones',
        required=False)
    registro_cosmetico_ids = fields.One2many(
        comodel_name='arsante.registro_cosmetico',
        inverse_name='tipo_registro_id',
        string='Registro Cosmetico',
        required=False)
    registro_desinfectantes_ids = fields.One2many(
        comodel_name='arsante.registro_desinfectantes',
        inverse_name='tipo_registro_id',
        string='Registro Desinfectantes',
        required=False)
    renovaciones_cosmeticos_ids = fields.One2many(
        comodel_name='arsante.renovaciones_cosmeticos',
        inverse_name='tipo_registro_id',
        string='Renovaciones Cosmeticos',
        required=False)
    renovaciones_desinfectantes_ids = fields.One2many(
        comodel_name='arsante.renovaciones_desinfectantes',
        inverse_name='tipo_registro_id',
        string='Renovaciones Desinfectantes',
        required=False)
    renovaciones_cosmeticas_ids = fields.One2many(
        comodel_name='arsante.renovaciones_cosmeticos',
        inverse_name='tipo_registro_id',
        string='Renovaciones Cosmeticas',
        required=False)
    registro_dispositivos_medicos_ids = fields.One2many(
        comodel_name='arsante.registro_dispositivos_medicos',
        inverse_name='tipo_registro_id',
        string='Registro Dispositivos Médicos',
        required=False)


    def open_tree_cda_cosmeticos(self):
        print(self._context)
        if self.tipo=='cda_cosmetico':
            act_window_id='arsante.cda_cosmetico_action_window'
            modelo='arsante.cda_cosmetico_dm'
        if self.tipo=='cda_uyd_alimentos':
            act_window_id='arsante.cda_uyd_alimentos_action_window'
            modelo='arsante.cda_uyd_alimentos'
        if self.tipo=='uyd_alimentos':
            act_window_id='arsante.uyd_alimentos_action_window'
            modelo='arsante.uyd_alimentos'
        if self.tipo=='dispositivos_medicos':
            act_window_id='arsante.dm_action_window'
            modelo='arsante.dispositivos_medicos'

        if self.tipo=='declaracion_dispositivos_medicos':
            act_window_id='arsante.declaracion_dm_action_window'
            modelo='arsante.declaracion_dispositivos_medicos'

        if self.tipo=='exim_proceso_cosmeticos':
            act_window_id='arsante.registro_isp_action_window'
            modelo='arsante.exim_proceso_cosmeticos'
        if self.tipo=='eximiciones_cosmeticos':
            act_window_id='arsante.eximicion_cosmeticos_action_window'
            modelo='arsante.eximiciones_cosmeticos'
        if self.tipo=='hds_hechas':
            act_window_id='arsante.hds_hechas_action_window'
            modelo='arsante.hds_hechas'

        if self.tipo=='inscripciones':
            act_window_id='arsante.inscripciones_action_window'
            modelo='arsante.inscripciones'

        if self.tipo=='inscripciones_cosmeticos':
            act_window_id='arsante.inscripciones_cosmeticos_action_window'
            modelo='arsante.inscripciones_cosmeticos'

        if self.tipo=='modificacion_cosmeticos':
            act_window_id='arsante.modificaciones_cosmetico_action_window'
            modelo='arsante.modificacion_cosmeticos'

        if self.tipo=='modificaciones_desinfectantes':
            act_window_id='arsante.modificaciones_desinfectantes_action_window'
            modelo='arsante.modificaciones_desinfectantes'

        if self.tipo=='rectificaciones':
            act_window_id='arsante.rectificaciones_action_window'
            modelo='arsante.rectificaciones'

        if self.tipo=='registro_cosmetico':
            act_window_id='arsante.registro_cosmetico_action_window'
            modelo='arsante.registro_cosmetico'

        if self.tipo=='registro_desinfectantes':
            act_window_id='arsante.registro_desinfectantes_action_window'
            modelo='arsante.registro_desinfectantes'

        if self.tipo=='renovaciones_cosmeticas':
            act_window_id='arsante.renovacion_cosmeticos_action_window'
            modelo='arsante.renovaciones_cosmeticos'

        if self.tipo=='renovaciones_desinfectantes':
            act_window_id='arsante.renovaciones_desinfectantes_action_window'
            modelo='arsante.renovaciones_desinfectantes'

        if self.tipo=='registro_dispositivos_medicos':
            act_window_id='arsante.registro_dispositivos_medicos_action_window'
            modelo='arsante.registro_dispositivos_medicos'


        return {
            "type": "ir.actions.act_window",
            "name": act_window_id,
            "res_model": modelo,
            "views": [[False, "tree"]],
            "res_id": self.env.context.get("id"),
        }


    @api.depends('cda_cosmetico_ids', 'registro_dispositivos_medicos_ids')
    def _compute_registros(self):
        for i in self:
            cda_cosmeticos_count = 0
            facturados = 0
            no_facturados = 0
            cotizados = 0
            no_cotizados = 0
            estado_listos = 0
            estado_no_listos = 0
            documentacion_completa = 0
            documentacion_completa_no_completa = 0
            para_renovar=0

            # Initialize all computed fields with default values
            i.para_renovar = 0
            i.total_record_count = 0
            i.facturados = 0
            i.no_facturados = 0
            i.cotizados = 0
            i.no_cotizados = 0
            i.estado_listos = 0
            i.estado_no_listos = 0
            i.documentacion_completa = 0
            i.documentacion_completa_no_completa = 0

            # CDA Alimentos
            if i.tipo=='cda_cosmetico':
                for cda in i.cda_cosmetico_ids:
                    cda_cosmeticos_count+=1
                    if cda.facturado==True:
                        facturados+=1
                    else:
                        no_facturados+=1
                    if cda.no_cotizado==False:
                        cotizados+=1
                    else:
                        no_cotizados+=1
                    if cda.estado=="listo":
                        estado_listos+=1
                    else:
                        estado_no_listos+=1
                    if cda.documentacion=="completa":
                        documentacion_completa+=1
                    else:
                        documentacion_completa_no_completa+=1
                    if cda.alerta_renovacion:
                        para_renovar+=1
                i.para_renovar=para_renovar
                i.total_record_count = cda_cosmeticos_count
                i.facturados=facturados
                i.no_facturados=no_facturados
                i.cotizados=cotizados
                i.no_cotizados=no_cotizados
                i.estado_listos=estado_listos
                i.estado_no_listos=estado_no_listos
                i.documentacion_completa=documentacion_completa
                i.documentacion_completa_no_completa=documentacion_completa_no_completa


            # registro_desinfectantes
            if i.tipo=='registro_desinfectantes':
                for cda in i.registro_desinfectantes_ids:
                    cda_cosmeticos_count+=1
                    if cda.facturado==True:
                        facturados+=1
                    else:
                        no_facturados+=1
                    if cda.no_cotizado==False:
                        cotizados+=1
                    else:
                        no_cotizados+=1
                    if cda.estado=="listo":
                        estado_listos+=1
                    else:
                        estado_no_listos+=1
                    if cda.documentacion=="completa":
                        documentacion_completa+=1
                    else:
                        documentacion_completa_no_completa+=1
                    if cda.alerta_renovacion:
                        para_renovar+=1
                i.para_renovar=para_renovar
                i.total_record_count = cda_cosmeticos_count
                i.facturados=facturados
                i.no_facturados=no_facturados
                i.cotizados=cotizados
                i.no_cotizados=no_cotizados
                i.estado_listos=estado_listos
                i.estado_no_listos=estado_no_listos
                i.documentacion_completa=documentacion_completa
                i.documentacion_completa_no_completa=documentacion_completa_no_completa
                i.para_renovar=para_renovar

            # renovaciones_cosmeticas
            if i.tipo=='renovaciones_cosmeticas':
                for cda in i.renovaciones_cosmeticas_ids:
                    cda_cosmeticos_count+=1
                    if cda.facturado==True:
                        facturados+=1
                    else:
                        no_facturados+=1
                    if cda.no_cotizado==False:
                        cotizados+=1
                    else:
                        no_cotizados+=1
                    if cda.estado=="listo":
                        estado_listos+=1
                    else:
                        estado_no_listos+=1
                    if cda.documentacion=="completa":
                        documentacion_completa+=1
                    else:
                        documentacion_completa_no_completa+=1
                    if cda.alerta_renovacion:
                        para_renovar+=1
                i.para_renovar=para_renovar
                i.total_record_count = cda_cosmeticos_count
                i.facturados=facturados
                i.no_facturados=no_facturados
                i.cotizados=cotizados
                i.no_cotizados=no_cotizados
                i.estado_listos=estado_listos
                i.estado_no_listos=estado_no_listos
                i.documentacion_completa=documentacion_completa
                i.documentacion_completa_no_completa=documentacion_completa_no_completa


            # renovaciones_desinfectantes
            if i.tipo=='renovaciones_desinfectantes':
                for cda in i.renovaciones_desinfectantes_ids:
                    cda_cosmeticos_count+=1
                    if cda.facturado==True:
                        facturados+=1
                    else:
                        no_facturados+=1
                    if cda.no_cotizado==False:
                        cotizados+=1
                    else:
                        no_cotizados+=1
                    if cda.estado=="listo":
                        estado_listos+=1
                    else:
                        estado_no_listos+=1
                    if cda.documentacion=="completa":
                        documentacion_completa+=1
                    else:
                        documentacion_completa_no_completa+=1
                    if cda.alerta_renovacion:
                        para_renovar+=1
                i.para_renovar=para_renovar
                i.total_record_count = cda_cosmeticos_count
                i.facturados=facturados
                i.no_facturados=no_facturados
                i.cotizados=cotizados
                i.no_cotizados=no_cotizados
                i.estado_listos=estado_listos
                i.estado_no_listos=estado_no_listos
                i.documentacion_completa=documentacion_completa
                i.documentacion_completa_no_completa=documentacion_completa_no_completa

            # registro_cosmetico
            if i.tipo=='registro_cosmetico':
                for cda in i.registro_cosmetico_ids:
                    cda_cosmeticos_count+=1
                    if cda.facturado==True:
                        facturados+=1
                    else:
                        no_facturados+=1
                    if cda.no_cotizado==False:
                        cotizados+=1
                    else:
                        no_cotizados+=1
                    if cda.estado=="listo":
                        estado_listos+=1
                    else:
                        estado_no_listos+=1
                    if cda.documentacion=="completa":
                        documentacion_completa+=1
                    else:
                        documentacion_completa_no_completa+=1
                    if cda.alerta_renovacion:
                        para_renovar+=1
                i.para_renovar=para_renovar
                i.total_record_count = cda_cosmeticos_count
                i.facturados=facturados
                i.no_facturados=no_facturados
                i.cotizados=cotizados
                i.no_cotizados=no_cotizados
                i.estado_listos=estado_listos
                i.estado_no_listos=estado_no_listos
                i.documentacion_completa=documentacion_completa
                i.documentacion_completa_no_completa=documentacion_completa_no_completa

            # rectificaciones
            if i.tipo=='rectificaciones':
                for cda in i.rectificaciones_ids:
                    cda_cosmeticos_count+=1
                    if cda.facturado==True:
                        facturados+=1
                    else:
                        no_facturados+=1
                    if cda.no_cotizado==False:
                        cotizados+=1
                    else:
                        no_cotizados+=1
                    if cda.estado=="listo":
                        estado_listos+=1
                    else:
                        estado_no_listos+=1
                    if cda.documentacion=="completa":
                        documentacion_completa+=1
                    else:
                        documentacion_completa_no_completa+=1
                    if cda.alerta_renovacion:
                        para_renovar+=1
                i.para_renovar=para_renovar
                i.total_record_count = cda_cosmeticos_count
                i.facturados=facturados
                i.no_facturados=no_facturados
                i.cotizados=cotizados
                i.no_cotizados=no_cotizados
                i.estado_listos=estado_listos
                i.estado_no_listos=estado_no_listos
                i.documentacion_completa=documentacion_completa
                i.documentacion_completa_no_completa=documentacion_completa_no_completa

            # modificaciones_desinfectantes
            if i.tipo=='modificaciones_desinfectantes':
                for cda in i.modificaciones_desinfectantes_ids:
                    cda_cosmeticos_count+=1
                    if cda.facturado==True:
                        facturados+=1
                    else:
                        no_facturados+=1
                    if cda.no_cotizado==False:
                        cotizados+=1
                    else:
                        no_cotizados+=1
                    if cda.estado=="listo":
                        estado_listos+=1
                    else:
                        estado_no_listos+=1
                    if cda.documentacion=="completa":
                        documentacion_completa+=1
                    else:
                        documentacion_completa_no_completa+=1
                    if cda.alerta_renovacion:
                        para_renovar+=1
                i.para_renovar=para_renovar
                i.total_record_count = cda_cosmeticos_count
                i.facturados=facturados
                i.no_facturados=no_facturados
                i.cotizados=cotizados
                i.no_cotizados=no_cotizados
                i.estado_listos=estado_listos
                i.estado_no_listos=estado_no_listos
                i.documentacion_completa=documentacion_completa
                i.documentacion_completa_no_completa=documentacion_completa_no_completa

            # Modificacion Cosmeticos
            if i.tipo=='modificacion_cosmeticos':
                for cda in i.modificacion_cosmeticos_ids:
                    cda_cosmeticos_count+=1
                    if cda.facturado==True:
                        facturados+=1
                    else:
                        no_facturados+=1
                    if cda.no_cotizado==False:
                        cotizados+=1
                    else:
                        no_cotizados+=1
                    if cda.estado=="listo":
                        estado_listos+=1
                    else:
                        estado_no_listos+=1
                    if cda.documentacion=="completa":
                        documentacion_completa+=1
                    else:
                        documentacion_completa_no_completa+=1
                    if cda.alerta_renovacion:
                        para_renovar+=1
                i.para_renovar=para_renovar
                i.total_record_count = cda_cosmeticos_count
                i.facturados=facturados
                i.no_facturados=no_facturados
                i.cotizados=cotizados
                i.no_cotizados=no_cotizados
                i.estado_listos=estado_listos
                i.estado_no_listos=estado_no_listos
                i.documentacion_completa=documentacion_completa
                i.documentacion_completa_no_completa=documentacion_completa_no_completa


            # Inscripciones Cosméticos
            if i.tipo=='inscripciones_cosmeticos':
                for cda in i.inscripciones_cosmeticos_ids:
                    cda_cosmeticos_count+=1
                    if cda.facturado==True:
                        facturados+=1
                    else:
                        no_facturados+=1
                    if cda.no_cotizado==False:
                        cotizados+=1
                    else:
                        no_cotizados+=1
                    if cda.estado=="listo":
                        estado_listos+=1
                    else:
                        estado_no_listos+=1
                    if cda.documentacion=="completa":
                        documentacion_completa+=1
                    else:
                        documentacion_completa_no_completa+=1
                    if cda.alerta_renovacion:
                        para_renovar+=1
                i.para_renovar=para_renovar
                i.total_record_count = cda_cosmeticos_count
                i.facturados=facturados
                i.no_facturados=no_facturados
                i.cotizados=cotizados
                i.no_cotizados=no_cotizados
                i.estado_listos=estado_listos
                i.estado_no_listos=estado_no_listos
                i.documentacion_completa=documentacion_completa
                i.documentacion_completa_no_completa=documentacion_completa_no_completa

            # Inscripciones
            if i.tipo=='inscripciones':
                for cda in i.inscripciones_ids:
                    cda_cosmeticos_count+=1
                    if cda.facturado==True:
                        facturados+=1
                    else:
                        no_facturados+=1
                    if cda.no_cotizado==False:
                        cotizados+=1
                    else:
                        no_cotizados+=1
                    if cda.estado=="listo":
                        estado_listos+=1
                    else:
                        estado_no_listos+=1
                    if cda.documentacion=="completa":
                        documentacion_completa+=1
                    else:
                        documentacion_completa_no_completa+=1
                    if cda.alerta_renovacion:
                        para_renovar+=1
                i.para_renovar=para_renovar
                i.total_record_count = cda_cosmeticos_count
                i.facturados=facturados
                i.no_facturados=no_facturados
                i.cotizados=cotizados
                i.no_cotizados=no_cotizados
                i.estado_listos=estado_listos
                i.estado_no_listos=estado_no_listos
                i.documentacion_completa=documentacion_completa
                i.documentacion_completa_no_completa=documentacion_completa_no_completa

            # HDS Hechas
            if i.tipo=='hds_hechas':
                for cda in i.hds_hechas_ids:
                    cda_cosmeticos_count+=1
                    if cda.facturado==True:
                        facturados+=1
                    else:
                        no_facturados+=1
                    if cda.no_cotizado==False:
                        cotizados+=1
                    else:
                        no_cotizados+=1
                    if cda.estado=="listo":
                        estado_listos+=1
                    else:
                        estado_no_listos+=1
                    if cda.documentacion=="completa":
                        documentacion_completa+=1
                    else:
                        documentacion_completa_no_completa+=1
                    if cda.alerta_renovacion:
                        para_renovar+=1
                i.para_renovar=para_renovar
                i.total_record_count = cda_cosmeticos_count
                i.facturados=facturados
                i.no_facturados=no_facturados
                i.cotizados=cotizados
                i.no_cotizados=no_cotizados
                i.estado_listos=estado_listos
                i.estado_no_listos=estado_no_listos
                i.documentacion_completa=documentacion_completa
                i.documentacion_completa_no_completa=documentacion_completa_no_completa


            # eximiciones_cosmeticos
            if i.tipo=='eximiciones_cosmeticos':
                for cda in i.eximiciones_cosmeticos_ids:
                    cda_cosmeticos_count+=1
                    if cda.facturado==True:
                        facturados+=1
                    else:
                        no_facturados+=1
                    if cda.no_cotizado==False:
                        cotizados+=1
                    else:
                        no_cotizados+=1
                    if cda.estado=="listo":
                        estado_listos+=1
                    else:
                        estado_no_listos+=1
                    if cda.documentacion=="completa":
                        documentacion_completa+=1
                    else:
                        documentacion_completa_no_completa+=1
                    if cda.alerta_renovacion:
                        para_renovar+=1
                i.para_renovar=para_renovar
                i.total_record_count = cda_cosmeticos_count
                i.facturados=facturados
                i.no_facturados=no_facturados
                i.cotizados=cotizados
                i.no_cotizados=no_cotizados
                i.estado_listos=estado_listos
                i.estado_no_listos=estado_no_listos
                i.documentacion_completa=documentacion_completa
                i.documentacion_completa_no_completa=documentacion_completa_no_completa

            # CDA UYD Alimentos
            if i.tipo=='cda_uyd_alimentos':
                for cda in i.cda_uyd_alimentos_ids:
                    cda_cosmeticos_count+=1
                    if cda.facturado==True:
                        facturados+=1
                    else:
                        no_facturados+=1
                    if cda.no_cotizado==False:
                        cotizados+=1
                    else:
                        no_cotizados+=1
                    if cda.estado=="listo":
                        estado_listos+=1
                    else:
                        estado_no_listos+=1
                    if cda.documentacion=="completa":
                        documentacion_completa+=1
                    else:
                        documentacion_completa_no_completa+=1
                    if cda.alerta_renovacion:
                        para_renovar+=1
                i.para_renovar=para_renovar
                i.total_record_count = cda_cosmeticos_count
                i.facturados=facturados
                i.no_facturados=no_facturados
                i.cotizados=cotizados
                i.no_cotizados=no_cotizados
                i.estado_listos=estado_listos
                i.estado_no_listos=estado_no_listos
                i.documentacion_completa=documentacion_completa
                i.documentacion_completa_no_completa=documentacion_completa_no_completa

            # UYD Alimentos
            if i.tipo=='uyd_alimentos':
                for cda in i.uyd_alimentos_ids:
                    cda_cosmeticos_count+=1
                    if cda.facturado==True:
                        facturados+=1
                    else:
                        no_facturados+=1
                    if cda.no_cotizado==False:
                        cotizados+=1
                    else:
                        no_cotizados+=1
                    if cda.estado=="listo":
                        estado_listos+=1
                    else:
                        estado_no_listos+=1
                    if cda.documentacion=="completa":
                        documentacion_completa+=1
                    else:
                        documentacion_completa_no_completa+=1
                    if cda.alerta_renovacion:
                        para_renovar+=1
                i.para_renovar=para_renovar
                i.total_record_count = cda_cosmeticos_count
                i.facturados=facturados
                i.no_facturados=no_facturados
                i.cotizados=cotizados
                i.no_cotizados=no_cotizados
                i.estado_listos=estado_listos
                i.estado_no_listos=estado_no_listos
                i.documentacion_completa=documentacion_completa
                i.documentacion_completa_no_completa=documentacion_completa_no_completa

            # Registro Dispositivos Medicos
            if i.tipo=='registro_dispositivos_medicos':
                for cda in i.registro_dispositivos_medicos_ids:
                    cda_cosmeticos_count+=1
                    if cda.facturado==True:
                        facturados+=1
                    else:
                        no_facturados+=1
                    if cda.no_cotizado==False:
                        cotizados+=1
                    else:
                        no_cotizados+=1
                    if cda.estado=="listo":
                        estado_listos+=1
                    else:
                        estado_no_listos+=1
                    if cda.documentacion=="completa":
                        documentacion_completa+=1
                    else:
                        documentacion_completa_no_completa+=1
                    if cda.alerta_renovacion:
                        para_renovar+=1
                i.para_renovar=para_renovar
                i.total_record_count = cda_cosmeticos_count
                i.facturados=facturados
                i.no_facturados=no_facturados
                i.cotizados=cotizados
                i.no_cotizados=no_cotizados
                i.estado_listos=estado_listos
                i.estado_no_listos=estado_no_listos
                i.documentacion_completa=documentacion_completa
                i.documentacion_completa_no_completa=documentacion_completa_no_completa

            # Dispositivos Medicos
            if i.tipo=='dispositivos_medicos':
                for cda in i.dispositivos_medicos_ids:
                    cda_cosmeticos_count+=1
                    if cda.facturado==True:
                        facturados+=1
                    else:
                        no_facturados+=1
                    if cda.no_cotizado==False:
                        cotizados+=1
                    else:
                        no_cotizados+=1
                    if cda.estado=="listo":
                        estado_listos+=1
                    else:
                        estado_no_listos+=1
                    if cda.documentacion=="completa":
                        documentacion_completa+=1
                    else:
                        documentacion_completa_no_completa+=1
                    if cda.alerta_renovacion:
                        para_renovar+=1
                i.para_renovar=para_renovar
                i.total_record_count = cda_cosmeticos_count
                i.facturados=facturados
                i.no_facturados=no_facturados
                i.cotizados=cotizados
                i.no_cotizados=no_cotizados
                i.estado_listos=estado_listos
                i.estado_no_listos=estado_no_listos
                i.documentacion_completa=documentacion_completa
                i.documentacion_completa_no_completa=documentacion_completa_no_completa

            # Declaracion Dispositivos Medicos
            if i.tipo=='declaracion_dispositivos_medicos':
                for cda in i.declaracion_dispositivos_medicos_ids:
                    cda_cosmeticos_count+=1
                    if cda.facturado==True:
                        facturados+=1
                    else:
                        no_facturados+=1
                    if cda.no_cotizado==False:
                        cotizados+=1
                    else:
                        no_cotizados+=1
                    if cda.estado=="listo":
                        estado_listos+=1
                    else:
                        estado_no_listos+=1
                    if cda.documentacion=="completa":
                        documentacion_completa+=1
                    else:
                        documentacion_completa_no_completa+=1
                    if cda.alerta_renovacion:
                        para_renovar+=1
                i.para_renovar=para_renovar
                i.total_record_count = cda_cosmeticos_count
                i.facturados=facturados
                i.no_facturados=no_facturados
                i.cotizados=cotizados
                i.no_cotizados=no_cotizados
                i.estado_listos=estado_listos
                i.estado_no_listos=estado_no_listos
                i.documentacion_completa=documentacion_completa
                i.documentacion_completa_no_completa=documentacion_completa_no_completa

            # Exim. Proceso Cosmeticos
            if i.tipo=='exim_proceso_cosmeticos':
                for cda in i.exim_proceso_cosmeticos_ids:
                    cda_cosmeticos_count+=1
                    if cda.facturado==True:
                        facturados+=1
                    else:
                        no_facturados+=1
                    if cda.no_cotizado==False:
                        cotizados+=1
                    else:
                        no_cotizados+=1
                    if cda.estado=="listo":
                        estado_listos+=1
                    else:
                        estado_no_listos+=1
                    if cda.documentacion=="completa":
                        documentacion_completa+=1
                    else:
                        documentacion_completa_no_completa+=1
                    if cda.alerta_renovacion:
                        para_renovar+=1
                i.para_renovar=para_renovar
                i.total_record_count = cda_cosmeticos_count
                i.facturados=facturados
                i.no_facturados=no_facturados
                i.cotizados=cotizados
                i.no_cotizados=no_cotizados
                i.estado_listos=estado_listos
                i.estado_no_listos=estado_no_listos
                i.documentacion_completa=documentacion_completa
                i.documentacion_completa_no_completa=documentacion_completa_no_completa

        return True
