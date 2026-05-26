# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class RevAntecedentesDm(models.Model):
    _name = 'arsante.rev_antecedentes_dm'

    name = fields.Char(string='Nombre Registro', compute='_compute_name', store=True)

    @api.depends('tipo_registro_id', 'date', 'partner_id')
    def _compute_name(self):
        for rec in self:
            parts = []
            if rec.tipo_registro_id:
                parts.append(rec.tipo_registro_id.name)
            if rec.date:
                parts.append(rec.date.strftime('%d/%m/%Y'))
            if rec.partner_id:
                parts.append(rec.partner_id.name)
            rec.name = ' - '.join(parts) if parts else ''

    def _default_get(self):
        tipo_id = self.env['arsante.tipo_registro'].search([('tipo', '=', 'rev_antecedentes_dm')])
        return tipo_id

    tipo_registro_id = fields.Many2one(
        comodel_name='arsante.tipo_registro',
        string='Tipo de Registro',
        required=True, default=_default_get, readonly=True, store=True)
    date = fields.Date(string='Fecha Registro')
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Cliente',
        domain="['|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]")
    marca = fields.Selection([
        ('no_aplica', 'No Aplica'),
        ('todomoda', 'Todo Moda'),
        ('isadora', 'Isadora'),
    ], string='Marca')
    marca_url = fields.Char(string='URL OneDrive', compute='_compute_marca_url')
    ref_gicona_isp = fields.Char(string='Ref. Gicona ISP')
    nro_registro = fields.Char(string='Nro. Registro')
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Producto',
        domain="['|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]")
    fabricante_id = fields.Many2one(
        comodel_name='res.partner',
        string='Fabricante',
        domain="['|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]")
    pdf_resolucion = fields.Binary(string='PDF Resolución', attachment=True)
    pdf_resolucion_url = fields.Char(string='Link de Acceso Carpeta')
    nro_resolucion = fields.Char(string='Nro. Resolución')
    fecha_resolucion = fields.Date(string='Fecha Resolución')
    sale_order_id = fields.Many2one(comodel_name='sale.order', string='Nota de Venta')
    oc_facturacion = fields.Char(string='OC Facturación')
    invoice_ids = fields.Many2many('account.move', string='Facturas', related='sale_order_id.invoice_ids', readonly=True)
    correo_ids = fields.Char(string='Correos Electrónicos', placeholder='correo@correo.cl,correo2@correo.cl')
    comentario = fields.Text(string='Comentario')
    facturado = fields.Boolean(string='Facturado')
    no_cotizado = fields.Boolean(string='No Cotizado?')
    estado = fields.Selection(string='Estado', selection=[('listo', 'Listo'), ('no_listo', 'No Listo')], required=False)
    documentacion = fields.Selection(string='Documentacion', selection=[('completa', 'Completa'), ('incompleta', 'Incompleta')], required=False)
    requiere_renovacion = fields.Boolean(string='Requiere Renovacion?')
    fecha_renovacion = fields.Date(string='Fecha de Renovacion', required=False)
    alerta_renovacion = fields.Boolean(
        string='Alerta Renovacion?',
        required=False,
        compute='_compute_alerta_renovacion',
        store=True)
    importado = fields.Boolean(string='Importado en el general')
    active = fields.Boolean(string='Activo', default=True)
    imagen = fields.Binary(string='Imagen', attachment=True)
    nro_oc = fields.Char(string='Nro. OC')
    fecha_renovacion = fields.Date(string='Fecha Renovación')

    @api.depends('marca')
    def _compute_marca_url(self):
        for record in self:
            if record.marca == 'todomoda':
                record.marca_url = 'https://arsanteconsultores-my.sharepoint.com/personal/pmuquillaza_arsante_cl/_layouts/15/onedrive.aspx?id=%2Fpersonal%2Fpmuquillaza%5Farsante%5Fcl%2FDocuments%2F1%2E%20CLIENTES%20VIGENTES%20AR%20SANTE%202025%2F0%2E%20COLILLAS%20DE%20PAGO%20BIJOU%2FBIJOU%2F2%2E%20colillas%20de%20pago%20TODO%20MODA&ga=1'
            elif record.marca == 'isadora':
                record.marca_url = 'https://arsanteconsultores-my.sharepoint.com/personal/pmuquillaza_arsante_cl/_layouts/15/onedrive.aspx?id=%2Fpersonal%2Fpmuquillaza%5Farsante%5Fcl%2FDocuments%2F1%2E%20CLIENTES%20VIGENTES%20AR%20SANTE%202025%2F0%2E%20COLILLAS%20DE%20PAGO%20BIJOU%2FBIJOU%2F1%2E%20colillas%20de%20pago%20ISADORA&ga=1'
            else:
                record.marca_url = False

    def open_marca_link(self):
        self.ensure_one()
        if self.marca_url:
            url = self.marca_url if self.marca_url.startswith('http') else 'https://' + self.marca_url
            return {'type': 'ir.actions.act_url', 'url': url, 'target': 'new'}
        return True

    def open_pdf_resolucion_url(self):
        self.ensure_one()
        if self.pdf_resolucion_url:
            url = self.pdf_resolucion_url if self.pdf_resolucion_url.startswith('http') else 'https://' + self.pdf_resolucion_url
            return {'type': 'ir.actions.act_url', 'url': url, 'target': 'new'}
        return True

    @api.onchange('estado', 'no_cotizado', 'documentacion', 'facturado', 'sale_order_id')
    def _compute_dashboard(self):
        try:
            self.tipo_registro_id._compute_registros()
            record_id = self.ids[0]
            all_record_id = self.env['arsante.all_record'].search([
                ('tipo_registro_id', '=', self.tipo_registro_id.id),
                ('registro_id', '=', record_id)
            ], limit=1)
            if all_record_id:
                all_record_id.facturado = self.facturado
                all_record_id.no_cotizado = self.no_cotizado
                all_record_id.estado = self.estado
                all_record_id.documentacion = self.documentacion
                all_record_id.sale_order_id = self.sale_order_id
        except:
            pass

    def create_so(self):
        model_sale_order = self.env['sale.order']
        model_sale_order_line = self.env['sale.order.line']
        ids = self.env["arsante.rev_antecedentes_dm"].browse(self._context.get("active_ids", []))

        sale_order_line_ids = []
        now = datetime.now()
        sale_order_id = False
        for i in ids:
            if i.sale_order_id:
                raise ValidationError("Algunos registros ya tienen asociada una nota de venta!")
        for i in ids:
            if i.ref_gicona_isp and i.fabricante_id and i.product_id:
                if not sale_order_id:
                    value = {
                        'name': self.env['ir.sequence'].next_by_code('sale.order') or _('New'),
                        'date_order': now,
                        'partner_id': i.partner_id.id,
                        'tipo_registro_id': self.tipo_registro_id.id,
                    }
                    partner_id_1 = i.partner_id.id
                    sale_order_id = model_sale_order.create(value)
                Value = {
                    'name': 'Ref. Gicona ISP: ' + i.ref_gicona_isp + ' Fabricante: ' + i.fabricante_id.name + ((' Nro. Registro: ' + i.nro_registro) if i.nro_registro else ''),
                    'product_id': i.product_id.id,
                    'product_uom_qty': 1,
                    'product_uom': i.product_id.uom_id.id,
                    'order_id': sale_order_id.id
                }
                if partner_id_1 != i.partner_id.id:
                    raise ValidationError("No puede tener clientes distintos para crear una nota de venta!")
                rec = model_sale_order_line.create(Value)
                i.sale_order_id = sale_order_id.id
                sale_order_line_ids.append(rec.id)
            else:
                raise ValidationError("""A algunos registros les falta uno de los siguientes datos:
                              -Ref. Gicona ISP
                              -Fabricante
                              -Producto
                              """)
        # Crear referencia DTE con OC Facturación
        if sale_order_id:
            oc_value = False
            for i in ids:
                if i.oc_facturacion:
                    oc_value = i.oc_facturacion
                    break
                elif i.ref_gicona_isp:
                    oc_value = i.ref_gicona_isp
                    break
            if oc_value:
                doc_class_oc = self.env['sii.document_class'].search([('name', '=', 'Orden de Compra')], limit=1)
                if doc_class_oc:
                    sale_order_id.write({
                        'referencia_ids': [(0, 0, {
                            'fecha_documento': now.date(),
                            'folio': oc_value,
                            'sii_referencia_TpoDocRef': doc_class_oc.id,
                        })]
                    })

    @api.depends('estado', 'no_cotizado', 'documentacion', 'facturado', 'fecha_renovacion', 'requiere_renovacion')
    def _compute_alerta_renovacion(self):
        for i in self:
            if i.fecha_renovacion:
                diferencia_meses = (i.fecha_renovacion.year - datetime.now().year) * 12 + (i.fecha_renovacion.month - datetime.now().month)
                if diferencia_meses <= 3:
                    i.alerta_renovacion = True
                else:
                    i.alerta_renovacion = False
