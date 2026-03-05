/** @odoo-module **/

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class FlewstackDocumentPreviewDialog extends Component {
    static template = "flewstack_preview_documents.ReportPreviewDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        title: { type: String, optional: true },
        url: String,
    };

    openInNewTab() {
        window.open(this.props.url, "_blank", "noopener,noreferrer");
    }
}
