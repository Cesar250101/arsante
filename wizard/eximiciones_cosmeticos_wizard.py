import logging
from datetime import datetime
from odoo import models, fields, api, exceptions, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

_logger = logging.getLogger(__name__)


class MasiveDTEAcceptWizard(models.TransientModel):
    _name = "arsante.eximiciones_cosmeticos_wizard"
    _description = "Genera una nota de venta con los registro seleccionados"

    @api.multi
    def create_so(self):
        model_sale_order=self.env['sale.order']
        model_sale_order_line=self.env['sale.order.line']
        ids = self.env["arsante.eximiciones_cosmeticos"].browse(self._context.get("active_ids", []))

        sale_order_line_ids=[]
        now = datetime.now()
        sale_order_id=False
        nro_reg_insc_isp=""
        for i in ids:
            nro_reg_insc_isp=i.nro_reg_insc_isp if i.nro_reg_insc_isp else ""
            if i.clave_gicona:
                if not sale_order_id:
                    value={
                        'name':self.env['ir.sequence'].next_by_code('sale.order') or _('New'),
                        'date_order':now,
                        'partner_id':i.partner_id.id
                    }
                    partner_id_1=i.partner_id.id
                    sale_order_id=model_sale_order.create(value)
                Value={
                    'name':'GICONA: '+i.clave_gicona+' Nº reg./inscrip ISP: '+nro_reg_insc_isp,
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
                              -Gicona
                              """)
        rec.write({
            'order_line':[(6, 0, [sale_order_line_ids])]
        })