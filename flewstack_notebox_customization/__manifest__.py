# -*- coding: utf-8 -*-
{
    "name": "Flewstack Notebox Customization",
    "version": "1.0.0",
    "summary": "Adds product brands to templates and variants for Notebox.",
    "author": "Flewstack LLC",
    "license": "LGPL-3",
    "category": "Productivity",
    "depends": ["product", "sale_management", "point_of_sale", "purchase", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/product_brand_views.xml",
        "views/product_views.xml",
        "views/sale_report_views.xml",
        "views/currency_rate_display_views.xml",
    ],
    "installable": True,
}
