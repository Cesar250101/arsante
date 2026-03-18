import logging
from datetime import datetime
from odoo import models, fields, api, exceptions, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

_logger = logging.getLogger(__name__)


class MasiveDTEAcceptWizard(models.TransientModel):
    _name = "arsante.renovaciones_desinfectantes_wizard"
    _description = "Genera una nota de venta con los registro seleccionados"



    def archivar(self):
        ids = self.env["arsante.renovaciones_desinfectantes"].browse(self._context.get("active_ids", []))
        for i in ids:
            i.write({
                'active':False
            })

    def desarchivar(self):
        ids = self.env["arsante.renovaciones_desinfectantes"].browse(self._context.get("active_ids", []))
        for i in ids:
            i.write({
                'active':True
            }) 

    def create_so(self):
        model_sale_order=self.env['sale.order']
        model_sale_order_line=self.env['sale.order.line']
        ids = self.env["arsante.renovaciones_desinfectantes"].browse(self._context.get("active_ids", []))

        sale_order_line_ids=[]
        now = datetime.now()
        sale_order_id=False
        for i in ids:
            if i.sale_order_id:
                raise Warning("Algunos registros ya tienen asociada una nota de venta!")
        for i in ids:
            if i.product_id and i.clave_gicona:
                if not sale_order_id:
                    value={
                        'name':self.env['ir.sequence'].next_by_code('sale.order') or _('New'),
                        'date_order':now,
                        'partner_id':i.partner_id.id,
                        'tipo_registro_id':self.tipo_registro_id.id,
                    }
                    partner_id_1=i.partner_id.id
                    sale_order_id=model_sale_order.create(value)
                Value={
                    'name':'Nº reg./Insc. ISP: '+i.reg_insc_isp+' Clave Gicona: '+i.clave_gicona,
                    'product_id':i.product_id.id,
                    'product_uom_qty':1,
                    'product_uom':i.product_id.uom_id.id,
                    'order_id':sale_order_id.id
                }
                if partner_id_1!=i.partner_id.id:
                    raise Warning("No puede tener clientes distintos para crear una nota de venta!")

                rec=model_sale_order_line.create(Value)
                i.sale_order_id=sale_order_id.id
                sale_order_line_ids.append(rec.id)

            else:
                raise Warning("""A algunos registros les falta uno de los siguierntes datos:
                              -Producto
                              -Nº reg./Insc. ISP
                              -Clave Gicona
                              """)
        rec.write({
            'order_line':[(6, 0, [sale_order_line_ids])]
        })