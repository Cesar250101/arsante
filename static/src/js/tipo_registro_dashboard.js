/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class TipoRegistroDashboard extends Component {
    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.state = useState({
            records: [],
            total_global: 0,
            total_facturados: 0,
            total_no_facturados: 0,
            total_para_renovar: 0,
            loading: true,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const records = await this.orm.searchRead(
                "arsante.tipo_registro",
                [],
                [
                    "name", "tipo", "total_record_count", "facturados", "no_facturados",
                    "cotizados", "no_cotizados", "estado_listos", "estado_no_listos",
                    "documentacion_completa", "documentacion_completa_no_completa", "para_renovar"
                ]
            ) || [];

            let total_global = 0;
            let total_facturados = 0;
            let total_no_facturados = 0;
            let total_para_renovar = 0;

            records.forEach(r => {
                total_global += r.total_record_count || 0;
                total_facturados += r.facturados || 0;
                total_no_facturados += r.no_facturados || 0;
                total_para_renovar += r.para_renovar || 0;
            });

            this.state.records = records;
            this.state.total_global = total_global;
            this.state.total_facturados = total_facturados;
            this.state.total_no_facturados = total_no_facturados;
            this.state.total_para_renovar = total_para_renovar;
        } catch (error) {
            console.error("Error loading Tipo Registro Dashboard data:", error);
            this.state.records = [];
        } finally {
            this.state.loading = false;
        }
    }

    openTipoRegistro(recordId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "arsante.tipo_registro",
            res_id: recordId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openRecords(record) {
        let model = "";
        switch (record.tipo) {
            case 'cda_cosmetico': model = 'arsante.cda_cosmetico_dm'; break;
            case 'cda_uyd_alimentos': model = 'arsante.cda_uyd_alimentos'; break;
            case 'dispositivos_medicos': model = 'arsante.dispositivos_medicos'; break;
            case 'exim_proceso_cosmeticos': model = 'arsante.exim_proceso_cosmeticos'; break;
            case 'eximiciones_cosmeticos': model = 'arsante.eximiciones_cosmeticos'; break;
            case 'hds_hechas': model = 'arsante.hds_hechas'; break;
            case 'inscripciones': model = 'arsante.inscripciones'; break;
            case 'modificacion_cosmeticos': model = 'arsante.modificacion_cosmeticos'; break;
            case 'modificaciones_desinfectantes': model = 'arsante.modificaciones_desinfectantes'; break;
            case 'rectificaciones': model = 'arsante.rectificaciones'; break;
            case 'registro_cosmetico': model = 'arsante.registro_cosmetico'; break;
            case 'registro_desinfectantes': model = 'arsante.registro_desinfectantes'; break;
            case 'renovaciones_cosmeticas': model = 'arsante.renovaciones_cosmeticos'; break;
            case 'renovaciones_desinfectantes': model = 'arsante.renovaciones_desinfectantes'; break;
        }

        if (model) {
            this.action.doAction({
                type: "ir.actions.act_window",
                name: record.name,
                res_model: model,
                views: [[false, "list"], [false, "form"]],
                domain: [["tipo_registro_id", "=", record.id]],
                target: "current",
            });
        }
    }
}

TipoRegistroDashboard.template = "arsante.TipoRegistroDashboard";
TipoRegistroDashboard.components = {};

registry.category("actions").add("arsante_tipo_registro_dashboard", TipoRegistroDashboard);
