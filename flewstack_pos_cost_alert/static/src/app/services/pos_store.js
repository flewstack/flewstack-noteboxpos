/** @odoo-module **/
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    async setDiscountFromUI(line, val) {
        const product = line?.product_id;
        const threshold = product?.flewstack_threshold;
        const averageCost = product?.flewstack_average_cost;
        const priceUnit = line?.price_unit ?? 0;
        const isJordan = product?.flewstack_is_origin_jordan;

        const parsedDiscount =
            typeof val === "number" ? val : isNaN(parseFloat(val)) ? 0 : parseFloat(val);
        const discount = Math.min(Math.max(parsedDiscount || 0, 0), 100);
        const discountedUnitPrice = priceUnit * (1 - discount / 100);

        if (threshold && priceUnit > 0 && discountedUnitPrice <= threshold) {
            const showAmounts = isJordan || false;
            const body = showAmounts
                ? _t(
                      "This discount would drop the unit price to or below the threshold (%(threshold)s). Average cost: %(cost)s.",
                      {
                          threshold: this.env.utils.formatCurrency(threshold),
                          cost: this.env.utils.formatCurrency(averageCost ?? threshold),
                      }
                  )
                : _t("This discount is blocked for this product.");

            this.dialog.add(AlertDialog, {
                title: _t("Discount Blocked"),
                body,
            });
            return;
        }

        return await super.setDiscountFromUI(...arguments);
    },
});
