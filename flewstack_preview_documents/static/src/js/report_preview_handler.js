/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { getReportUrl } from "@web/webclient/actions/reports/utils";
import { FlewstackDocumentPreviewDialog } from "./report_preview_dialog";

const SUPPORTED_MODELS = new Set(["sale.order"]);
const SUPPORTED_REPORT_NAMES = new Set([
    "account.report_invoice",
    "account.report_invoice_with_payments",
    "sale.report_saleorder",
    "sale.report_saleorder_pro_forma",
]);
const ACCOUNT_INVOICE_REPORT_NAMES = new Set([
    "account.report_invoice",
    "account.report_invoice_with_payments",
]);
const ACCOUNT_INVOICE_MOVE_TYPES = new Set([
    "out_invoice",
    "out_refund",
    "out_receipt",
    "in_invoice",
    "in_refund",
    "in_receipt",
]);

function getActiveMoveIds(action) {
    const activeIds = action.context?.active_ids;
    if (Array.isArray(activeIds) && activeIds.length) {
        return activeIds;
    }
    if (typeof action.context?.active_id === "number") {
        return [action.context.active_id];
    }
    return [];
}

function shouldPreviewReport(action) {
    if (action.report_type !== "qweb-pdf") {
        return false;
    }
    if (action.device_ids?.length) {
        return false;
    }

    const activeModel = action.context?.active_model || action.model;
    if (SUPPORTED_MODELS.has(activeModel)) {
        return true;
    }

    return SUPPORTED_REPORT_NAMES.has(action.report_name);
}

async function hasNonInvoiceMoves(action, env) {
    const activeModel = action.context?.active_model || action.model;
    if (activeModel !== "account.move") {
        return false;
    }
    if (!ACCOUNT_INVOICE_REPORT_NAMES.has(action.report_name)) {
        return false;
    }

    const ids = getActiveMoveIds(action);
    if (!ids.length) {
        return false;
    }

    const moves = await env.services.orm.read("account.move", ids, ["move_type"]);
    return moves.some((move) => !ACCOUNT_INVOICE_MOVE_TYPES.has(move.move_type));
}

async function previewDocumentsHandler(action, options, env) {
    if (!shouldPreviewReport(action)) {
        return false;
    }
    if (await hasNonInvoiceMoves(action, env)) {
        env.services.notification.add(
            _t("Invoice PDF is only available for invoices and receipts."),
            { type: "warning" }
        );
        options?.onClose?.();
        return true;
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
