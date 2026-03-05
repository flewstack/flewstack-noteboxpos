/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup();
        const order = this.currentOrder;
        if (order && !order.isToInvoice()) {
            order.setToInvoice(true);
        }
    },
});
