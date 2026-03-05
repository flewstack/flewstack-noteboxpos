# -*- coding: utf-8 -*-
{
    "name": "Landed Cost Product Summary",
    "version": "1.0.0",
    "summary": "Show landed cost totals grouped by product with XLSX export.",
    "author": "Flewstack LLC",
    "license": "LGPL-3",
    "category": "Inventory",
    "depends": ["stock_landed_costs"],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_landed_cost_product_report_views.xml",
        "views/stock_landed_cost_views.xml",
    ],
    "installable": True,
}
