/** @odoo-module */

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    get canBeRemoved() {
        if (!this.product_id || !this.product_id.uom_id) {
            return false;
        }
        return this.product_id.uom_id.isZero(this.qty);
    },
});
