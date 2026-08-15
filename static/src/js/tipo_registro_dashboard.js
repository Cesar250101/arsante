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

    /**
     * Abre los registros de un tipo.
     *
     * Antes había aquí un switch de 14 casos que mapeaba el tipo a su modelo,
     * y que dejaba fuera a 8 tipos por no haberse actualizado. Ahora la acción
     * la construye el servidor, que es la única fuente de verdad.
     */
    async openRecords(record) {
        await this._abrir(record, "action_open_registros");
    }

    async openNoFacturados(record) {
        await this._abrir(record, "action_open_no_facturados");
    }

    async openNoCotizados(record) {
        await this._abrir(record, "action_open_no_cotizados");
    }

    async openParaRenovar(record) {
        await this._abrir(record, "action_open_para_renovar");
    }

    async _abrir(record, metodo) {
        const action = await this.orm.call(
            "arsante.tipo_registro", metodo, [[record.id]]
        );
        if (action) {
            this.action.doAction(action);
        }
    }
}

TipoRegistroDashboard.template = "arsante.TipoRegistroDashboard";
TipoRegistroDashboard.components = {};

registry.category("actions").add("arsante_tipo_registro_dashboard", TipoRegistroDashboard);
