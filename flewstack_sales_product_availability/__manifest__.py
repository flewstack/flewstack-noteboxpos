# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Flewstack Sales Product Availability",
    "version": "1.0.1",
    "category": "Sales/Sales",
    "summary": "Sleek per-location and per-warehouse availability popup on sale order lines",
    "depends": ["sale_stock"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/sales_product_availability_views.xml",
        "views/sale_order_history_views.xml",
        "views/sale_order_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "flewstack_sales_product_availability/static/src/scss/sales_product_availability.scss",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
