# -*- coding: utf-8 -*-
{
    'name': "arsante",

    'summary': """
                    Localización Arsante.
                """,

    'description': """
        Long description of module's purpose
    """,

    'author': "Method",
    'website': "https://www.method.cl",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account','sale','contacts'],

    # always loaded
    'data': [
        'data/groups.xml',
        'data/cron.xml',
        'security/ir.model.access.csv',
         'data/tipo_registro.xml',
         'views/all_record.xml',
        'views/exim_proceso_cosmeticos.xml',
        'views/templates.xml',
        'views/cda_cosmetico_dm.xml',
        'views/modificacion_cosmeticos.xml',
        'views/registro_cosmetico.xml',
        'views/inscripciones.xml',
        'views/inscripciones_cosmeticos.xml',
        'views/rectificaciones.xml',
        'views/cda_uyd_alimentos.xml',
        'views/uyd_alimentos.xml',
        'views/registro_dispositivos_medicos.xml',
        'views/declaracion_dispositivos_medicos.xml',
        'views/dispositivos_medicos.xml',
        'views/eximiciones_cosmeticos.xml',
        'views/renovaciones_cosmeticas.xml',
        'views/registro_desinfectantes.xml',
        'views/modificaciones_desinfectantes.xml',
        'views/renovaciones_desinfectantes.xml',
        'views/hds_hechas.xml',
        'wizard/exim_proceso_cosmeticos_wizard.xml',
        'wizard/cda_cosmetico_dm_wizard.xml',
        'wizard/modificacion_cosmeticos_wizard.xml',
        'wizard/registro_cosmetico_wizard.xml',
        'wizard/inscripciones_wizard.xml',
        'wizard/cda_uyd_alimentos_wizard.xml',
        'wizard/dispositivos_medicos_wizard.xml',
        'views/dashboard.xml',
        'wizard/eximiciones_cosmeticos_wizard.xml',
        'wizard/hds_hechas_wizard.xml',
        'wizard/rectificaciones_wizard.xml',
        'wizard/renovaciones_cosmeticas_wizard.xml',
        'wizard/registro_desinfectantes_wizard.xml',
        'wizard/modificaciones_desinfectantes_wizard.xml',
        'wizard/renovaciones_desinfectantes_wizard.xml',
        'views/tipo_registro.xml',
        'views/tipo_regitro.xml',
        'views/res_company.xml',
        'views/sale_order.xml',
        'report/sale_order_report.xml',
        'report/account_move_report.xml',
        'views/account_move.xml',
        'views/res_partner.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'arsante/static/src/css/tipo_registro_dashboard.css',
            'arsante/static/src/js/tipo_registro_dashboard.js',
            'arsante/static/src/xml/tipo_registro_dashboard.xml',
        ],
    },
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}