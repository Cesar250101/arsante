/** @odoo-module **/

import { registerPatch } from "@mail/model/model_core";

/**
 * Las notificaciones de asignación se vinculan a arsante.registro. Odoo abre
 * por defecto el hilo de Discuss al pulsarlas; para este modelo se navega
 * directamente al formulario del trámite asignado.
 */
registerPatch({
    name: "ThreadNeedactionPreviewView",
    recordMethods: {
        onClick(ev) {
            if (!this.exists()) {
                return;
            }
            const markAsRead = this.markAsReadRef.el;
            if (markAsRead && markAsRead.contains(ev.target)) {
                return;
            }
            if (this.thread.model !== "arsante.registro") {
                return this._super(...arguments);
            }

            this.messaging.models["Message"].markAllAsRead([
                ["model", "=", this.thread.model],
                ["res_id", "=", this.thread.id],
            ]);
            this.env.services.action.doAction({
                type: "ir.actions.act_window",
                res_model: "arsante.registro",
                res_id: this.thread.id,
                view_mode: "form",
                views: [[false, "form"]],
                target: "current",
            });
            if (!this.messaging.device.isSmall) {
                this.messaging.messagingMenu.close();
            }
        },
    },
});
