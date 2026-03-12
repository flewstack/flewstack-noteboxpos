# -*- coding: utf-8 -*-
{
    "name": "Flewstack Preview Documents",
    "version": "19.0.1.1.0",
    "summary": "Preview quotations, invoices, and delivery slips in Odoo instead of downloading PDF files.",
    "author": "Flewstack LLC",
    "category": "Sales/Inventory/Invoicing",
    "license": "LGPL-3",
    "depends": ["web", "sale", "account", "stock"],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "flewstack_preview_documents/static/src/js/report_preview_dialog.js",
            "flewstack_preview_documents/static/src/js/report_preview_handler.js",
            "flewstack_preview_documents/static/src/xml/report_preview_dialog.xml",
            "flewstack_preview_documents/static/src/scss/report_preview_dialog.scss",
        ],
    },
    "installable": True,
    "application": False,
}
