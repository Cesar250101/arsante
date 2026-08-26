/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class TipoRegistroDashboard extends Component {
    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.state = useState({
            groups: [],
            total_global: 0,
            total_facturados: 0,
            total_no_facturados: 0,
            total_con_nota_venta: 0,
            total_sin_nota_venta: 0,
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
                    "name", "tipo", "grupo_id", "total_record_count", "facturados", "no_facturados",
                    "cotizados", "no_cotizados", "estado_listos", "estado_no_listos",
                    "documentacion_completa", "documentacion_completa_no_completa", "para_renovar"
                ]
            ) || [];

            let total_global = 0;
            let total_facturados = 0;
            let total_no_facturados = 0;
            let total_con_nota_venta = 0;
            let total_sin_nota_venta = 0;
            let total_para_renovar = 0;

            records.forEach(r => {
                // El complemento de las notas de venta se calcula desde la
                // misma fuente: total de registros menos sale_order_id.
                // También evita un valor vacío si el navegador conserva una
                // respuesta anterior sin no_cotizados.
                r.no_cotizados = Math.max(
                    0,
                    (r.total_record_count || 0) - (r.cotizados || 0)
                );
                total_global += r.total_record_count || 0;
                total_facturados += r.facturados || 0;
                total_no_facturados += r.no_facturados || 0;
                total_con_nota_venta += r.cotizados || 0;
                total_sin_nota_venta += r.no_cotizados || 0;
                total_para_renovar += r.para_renovar || 0;
            });

            this.state.groups = await this._agruparPorGrupo(records);
            this.state.total_global = total_global;
            this.state.total_facturados = total_facturados;
            this.state.total_no_facturados = total_no_facturados;
            this.state.total_con_nota_venta = total_con_nota_venta;
            this.state.total_sin_nota_venta = total_sin_nota_venta;
            this.state.total_para_renovar = total_para_renovar;
        } catch (error) {
            console.error("Error loading Tipo Registro Dashboard data:", error);
            this.state.groups = [];
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Junta las tarjetas por arsante.tipo_registro.grupo, en el mismo orden
     * (sequence, name) que la pantalla de administración de grupos. Los
     * tipos sin grupo van al final, bajo "Sin grupo". Si nadie usa grupos
     * todavía, no tiene sentido mostrar encabezados de sección: se deja como
     * una sola lista plana, igual que antes.
     */
    async _agruparPorGrupo(records) {
        const idsGrupo = [...new Set(
            records.filter(r => r.grupo_id).map(r => r.grupo_id[0])
        )];

        let ordenGrupos = [];
        if (idsGrupo.length) {
            ordenGrupos = await this.orm.searchRead(
                "arsante.tipo_registro.grupo",
                [["id", "in", idsGrupo]],
                ["name"],
                { order: "sequence, name" },
            );
        }

        const porId = new Map();
        for (const g of ordenGrupos) {
            porId.set(g.id, { id: g.id, name: g.name, records: [] });
        }
        const sinGrupo = { id: false, name: "Sin grupo", records: [] };

        for (const record of records) {
            if (record.grupo_id && porId.has(record.grupo_id[0])) {
                porId.get(record.grupo_id[0]).records.push(record);
            } else {
                sinGrupo.records.push(record);
            }
        }

        const grupos = [...porId.values()];
        if (sinGrupo.records.length) {
            grupos.push(sinGrupo);
        }
        return grupos;
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
