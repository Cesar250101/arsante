# -*- coding: utf-8 -*-
"""Arsante public controllers."""

import logging
import json

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class ArsanteOnboardingController(http.Controller):
    """Receives onboarding JSON payloads and builds partner records."""



    @staticmethod
    def _clean(values):
        return {k: v for k, v in values.items() if v not in (False, None, "")}

    @staticmethod
    def _extract_record(payload):
        if isinstance(payload, list):
            payload = payload[0] if payload else {}
        if not isinstance(payload, dict):
            raise ValueError("Payload must be a JSON object or list of objects")
        return payload

    def _create_company_partner(self, data):
        partner_vals = self._clean(
            {
                "name": data.get("nombre_empresa") or data.get("name"),
                "vat": data.get("rut_empresa") or data.get("document_number"),
                "comment": data.get("giro") or data.get("activity_description"),
                "street": data.get("direccion") or data.get("street"),
                "city": data.get("comuna") or data.get("city_id"),
                "email": data.get("email"),
                "phone": data.get("telefono"),
                "company_type": "company",
                "company_id": data.get("company_id") or request.env.company.id,
            }
        )
        if not partner_vals.get("name"):
            raise ValueError("El campo 'nombre_empresa' (o 'name') es obligatorio")
        return request.env["res.partner"].sudo().create(partner_vals)
        print (partner_vals)


    def _create_rp_contact(self, company_partner, data):
        rp_vals = self._clean(
            {
                "name": data.get("nombre_rp"),
                "vat": data.get("rut_rp"),
                "street": data.get("direccion_rp"),
                "mobile": data.get("mobil"),
                "email": data.get("email_rp"),
                "parent_id": company_partner.id,
                "company_type": "person",
                "company_id": data.get("company_id") or request.env.company.id,
            }
        )
        if not rp_vals.get("name"):
            return False
        return request.env["res.partner"].sudo().create(rp_vals)

    def _create_bank_account(self, company_partner, data):
        acc_number = data.get("numero_cuenta")
        if not acc_number:
            return False

        bank_record = False
        bank_name = data.get("banco")
        if bank_name:
            bank_env = request.env["res.bank"].sudo()
            bank_record = bank_env.search([("name", "=", bank_name)], limit=1)
            if not bank_record:
                bank_record = bank_env.create({"name": bank_name})

        bank_vals = self._clean(
            {
                "partner_id": company_partner.id,
                "acc_holder_name": data.get("nombre_titular"),
                "acc_number": acc_number,
                "bank_id": bank_record.id if bank_record else False,
            }
        )
        # Store auxiliary information in the partner chatter to avoid losing data.
        notes = []
        if data.get("rut_tb"):
            notes.append(f"RUT titular: {data['rut_tb']}")
        if data.get("tipo_cuenta"):
            notes.append(f"Tipo cuenta: {data['tipo_cuenta']}")
        if data.get("email_tb"):
            notes.append(f"Email titular: {data['email_tb']}")
        if notes:
            company_partner.message_post(body=" | ".join(notes))

        return request.env["res.partner.bank"].sudo().create(bank_vals)

    @http.route(
        "/arsante/api/onboarding",
        type="http",

        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def receive_onboarding(self, **kwargs):
        try:
            # Parse raw JSON data
            raw_data = request.httprequest.data
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                return request.make_response(
                    json.dumps({"status": "error", "message": "Invalid JSON format"}),
                    headers=[("Content-Type", "application/json")],
                    status=400
                )

            # Support both JSON-RPC style ("params" wrapper) and raw JSON
            if "params" in data:
                data = data["params"]
            
            # Log successful receipt
            _logger.info("Controller HTTP receive_onboarding called with data: %s", data)

            company_partner = self._create_company_partner(data)
            rp_contact = self._create_rp_contact(company_partner, data)
            bank_account = self._create_bank_account(company_partner, data)
            
            result = {
                "status": "ok",
                "partner_id": company_partner.id,
                "rp_partner_id": rp_contact.id if rp_contact else False,
                "bank_account_id": bank_account.id if bank_account else False,
            }
            return request.make_response(
                json.dumps(result),
                headers=[("Content-Type", "application/json")]
            )
            
        except Exception as exc:
            request.env.cr.rollback()
            _logger.exception("Arsante onboarding controller error")
            return request.make_response(
                json.dumps({"status": "error", "message": str(exc)}),
                headers=[("Content-Type", "application/json")],
                status=500
            )