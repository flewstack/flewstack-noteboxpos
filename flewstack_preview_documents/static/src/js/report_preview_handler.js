/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { getReportUrl } from "@web/webclient/actions/reports/utils";
import { FlewstackDocumentPreviewDialog } from "./report_preview_dialog";

const SUPPORTED_MODELS = new Set(["account.move", "sale.order", "stock.picking"]);
const SUPPORTED_REPORT_NAMES = new Set([
    "account.report_invoice",
    "account.report_invoice_with_payments",
    "sale.report_saleorder",
    "sale.report_saleorder_pro_forma",
    "stock.report_deliveryslip",
    "stock.report_delivery_document",
    "stock.action_report_delivery",
]);

function getActionContext(action) {
    if (!action?.context) {
        return {};
    }
    if (typeof action.context === "object") {
        return action.context;
    }
    if (typeof action.context === "string") {
        try {
            return JSON.parse(action.context);
        } catch {
            return {};
        }
    }
    return {};
}

function shouldPreviewReport(action) {
    if (action.report_type !== "qweb-pdf") {
        return false;
    }
    if (action.device_ids?.length) {
        return false;
    }

    const context = getActionContext(action);
    const activeModel =
        context.active_model ||
        action.model ||
        action.res_model ||
        action.data?.model ||
        null;
    const reportName = action.report_name || action.report_file || action.xml_id || null;

    if (SUPPORTED_MODELS.has(activeModel)) {
        return true;
    }

    if (SUPPORTED_REPORT_NAMES.has(reportName)) {
        return true;
    }

    // Delivery reports can vary by report name across versions/customizations.
    return activeModel === "stock.picking" && typeof reportName === "string" && reportName.startsWith("stock.");
}

async function previewDocumentsHandler(action, options, env) {
    if (!shouldPreviewReport(action)) {
        return false;
    }

    const reportUrl = getReportUrl(action, "pdf", user.context);
    env.services.dialog.add(FlewstackDocumentPreviewDialog, {
        title: action.display_name || action.name || _t("Document Preview"),
        url: reportUrl,
    });

    if (action.close_on_report_download) {
        await env.services.action.doAction(
            { type: "ir.actions.act_window_close" },
            { onClose: options?.onClose }
        );
        return true;
    }

    options?.onClose?.();
    return true;
}

registry.category("ir.actions.report handlers").add(
    "flewstack_preview_documents_handler",
    previewDocumentsHandler,
    { sequence: 80 }
);
