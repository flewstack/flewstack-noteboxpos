# -*- coding: utf-8 -*-
{
    "name": "Flewstack POS Cost Alert",
    "version": "1.0.0",
    "category": "Point of Sale",
    "summary": "Protect POS discounts using cost-based thresholds on products.",
    "author": "Flewstack LLC",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "data": [
        "views/product_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "flewstack_pos_cost_alert/static/src/**/*",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
}
