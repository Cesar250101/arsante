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
    # 2.0.0 -> Odoo ejecuta migrations/16.0.2.0.0/ (modelo genérico con campos
    # dinámicos). NO bajar esta versión: los scripts de migración sólo corren
    # una vez, al detectar que la instalada es anterior.
    'version': '2.1.6',

    # any module necessary for this one to work correctly
    'depends': ['base','account','sale','contacts'],

    # always loaded
    'data': [
        'data/groups.xml',
        'security/ir.model.access.csv',
        'data/tipo_registro.xml',
        'data/tipo_registro_plantillas.xml',
        # Menús raíz: deben cargarse antes que cualquier vista que cuelgue de
        # ellos. Los menús de cada tipo de trámite ya no se declaran en XML,
        # los genera arsante.tipo_registro._sync_menu().
        'views/menus.xml',
        # Modelo genérico con campos definidos por el usuario
        'views/registro.xml',
        'views/campo.xml',
        'views/templates.xml',
        'views/marcas.xml',
        'views/tipo_servicio.xml',
        'views/dashboard.xml',
        'views/tipo_registro.xml',
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
            'arsante/static/src/css/menu_separators.css',
            'arsante/static/src/js/tipo_registro_dashboard.js',
            'arsante/static/src/xml/tipo_registro_dashboard.xml',
        ],
    },
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}