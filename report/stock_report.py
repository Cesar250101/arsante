# Copyright 2020 Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields, tools

class Ventas(models.Model):
    _name = 'method_minori.ventas_report'
    _description = "Ventas por marca"
    _auto = False
    _order = 'product_id desc'

    tipodocto = fields.Char(string='Tipo Documento')    
    date_order = fields.Date(string='Fecha Orden')    
    cliente_id = fields.Many2one(comodel_name='res.partner', string='Cliente')
    product_product_id = fields.Many2one(comodel_name='product.product', string='Producto')
    product_template_id = fields.Many2one(comodel_name='product.template', string='Plantilla Producto')
    cantidad = fields.Integer(string='Cantidad')    
    price_unit = fields.Integer(string='Precio Unitario')
    price_subtotal = fields.Integer(string='Subtotal Línea')
    marca_id = fields.Many2one(comodel_name='method_minori.marcas', string='Marca')
    categ_id = fields.Many2one(comodel_name='product.category', string='Categoria Producto')
    user_id = fields.Many2one(
        're.users',
        string='Usuario',
        readonly=True,
    )    
    comision = fields.Integer(string='Comisión Marca')
    comision_marca = fields.Char(string='Comisión Marca')    


    @api.model_cr
    def init(self):
        user=self.env.uid
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (SELECT 
                ROW_NUMBER() OVER() AS id,
                sdc.name as tipodocto,
                po.date_order,
                rp.id as cliente_id,
                pp.id as product_product_id,
                pt.id as product_template_id,
                pol.qty as cantidad,
                pol.price_unit,
                pol.price_subtotal,
                mmm.id as marca_id,
                pc.id as categ_id,
                mmm.user_id,
                mmm.comision_marca ,
                round((pol.price_subtotal * (mmm.comision_marca/100))) as comision
                from pos_order po inner join sii_document_class sdc on po.document_class_id =sdc.id
                inner join pos_order_line pol on po.id =pol.order_id 
                inner join product_product pp on pol.product_id =pp.id
                inner join product_template pt on pp.product_tmpl_id =pt.id  
                left join res_partner rp on po.partner_id =rp.id
                inner join method_minori_marcas mmm on pt.marca_id =mmm.id
                inner join product_category pc on pt.categ_id =pc.id
            )
        """ % (
            self._table
            #self._select(), self._from(),user, self._group_by(), self._having(),

        ))



class StockReport(models.Model):
    _name = 'method_minori.stock_report'
    _description = "Respote stock por proveedor"
    _auto = False
    _order = 'product_id desc'

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        readonly=True,
    )
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product Template',
        readonly=True,
    )
    product_categ_id = fields.Many2one(
        'product.category',
        string='Product Category',
        readonly=True,
    )
    stock = fields.Integer(
        string="Stock",
        readonly=True,
    )
    marca_id = fields.Many2one(
        'method_minori.marcas',
        string='Marca',
        readonly=True,
    )

    user_id = fields.Many2one(
        're.users',
        string='Usuario',
        readonly=True,
    )
    precio_venta = fields.Integer(string='Precio de Venta')
    




    @api.model_cr
    def init(self):
        user=self.env.uid
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (SELECT 
                ROW_NUMBER() OVER() AS id,
                sq.product_id AS product_id,
                pp.product_tmpl_id ,
                pt.categ_id AS product_categ_id,
                sum(sq.quantity) AS Stock,
                pt.marca_id,
                mmm.user_id,pt.list_price AS precio_venta
                FROM stock_quant sq, product_product pp ,product_template pt,method_minori_marcas mmm,stock_location sl  
                where sq.product_id =pp.id 
                and pp.product_tmpl_id =pt.id
                and pt.marca_id =mmm.id
                and sq.location_id =sl.id 
                and sl.usage='internal'
                and pt.active=true
                group by sq.product_id ,pp.product_tmpl_id ,pt.categ_id ,pt.marca_id,mmm.user_id,pt.list_price    
                
            )
        """ % (
            self._table
            #self._select(), self._from(),user, self._group_by(), self._having(),

        ))
