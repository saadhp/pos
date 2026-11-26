import {PosStore} from "@point_of_sale/app/store/pos_store";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async initServerData() {
        const res = await super.initServerData(...arguments);
        this.data.connectWebSocket(
            "LIVE_PAYMENT_METHOD_ADDED",
            this.onLivePaymentMethodAdded.bind(this)
        );
        return res;
    },

    async onLivePaymentMethodAdded(payload) {
        if (!payload || payload.config_id !== this.config.id) {
            return;
        }
        try {
            if (payload.payment_method_ids && payload.payment_method_ids.length) {
                await this.data.read("pos.payment.method", payload.payment_method_ids);
            }
            await this.data.read("pos.config", [this.config.id]);
            await this.data.read("pos.session", [this.session.id]);

            const names = (payload.payment_method_names || []).join(", ");
            if (this.notification) {
                this.notification.add(_t("New payment method added: %s", names), {
                    type: "info",
                });
            }
        } catch {
            // Session data will refresh on next reload if offline
        }
    },
});
