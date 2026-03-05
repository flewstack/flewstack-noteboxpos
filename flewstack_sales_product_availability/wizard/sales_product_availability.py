# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SalesProductAvailability(models.TransientModel):
    _name = "flewstack_sales_product_availability"
    _description = "Product Availability for Sale Order Line"

    sale_line_id = fields.Many2one("sale.order.line", required=True, ondelete="cascade")
    product_id = fields.Many2one(related="sale_line_id.product_id", readonly=True)
    product_uom_id = fields.Many2one(related="sale_line_id.product_uom_id", readonly=True)
    company_id = fields.Many2one(related="sale_line_id.company_id", readonly=True)
    warehouse_line_ids = fields.One2many(
        "flewstack_sales_product_availability_warehouse_line",
        "wizard_id",
        string="Warehouse Availability",
    )
    location_line_ids = fields.One2many(
        "flewstack_sales_product_availability_location_line",
        "wizard_id",
        string="Location Availability",
    )
    customer_product_history_ids = fields.One2many(
        "flewstack_sales_product_availability_history_line",
        "wizard_id",
        string="Customer Product History",
    )

    def _fill_availability_lines(self):
        """Compute availability per warehouse and per location for the wizard product."""
        for wizard in self:
            wizard.warehouse_line_ids = [(5, 0, 0)]
            wizard.location_line_ids = [(5, 0, 0)]
            wizard.customer_product_history_ids = [(5, 0, 0)]

            sale_line = wizard.sale_line_id
            if not sale_line.product_id or not sale_line.product_id.is_storable:
                continue

            product = sale_line.product_id
            company = sale_line.company_id

            def _to_line_uom(qty):
                return product.uom_id._compute_quantity(qty, sale_line.product_uom_id)

            warehouses = (
                self.env["stock.warehouse"]
                .with_company(company)
                .sudo()
                .search([("company_id", "=", company.id)], order="sequence, id")
            )
            warehouse_commands = []
            for warehouse in warehouses:
                product_data = (
                    product.with_context(
                        warehouse_id=warehouse.id,
                        company_id=company.id,
                    )
                    .sudo()
                    .read(["qty_available", "free_qty", "virtual_available"])
                )
                qty_on_hand = product_data[0]["qty_available"] if product_data else 0.0
                free_qty = product_data[0]["free_qty"] if product_data else 0.0
                qty_forecasted = (
                    product_data[0]["virtual_available"] if product_data else 0.0
                )
                qty_reserved = qty_on_hand - free_qty
                warehouse_commands.append(
                    (
                        0,
                        0,
                        {
                            "warehouse_id": warehouse.id,
                            "qty_on_hand": _to_line_uom(qty_on_hand),
                            "qty_reserved": _to_line_uom(qty_reserved),
                            "qty_available": _to_line_uom(free_qty),
                            "qty_forecasted": _to_line_uom(qty_forecasted),
                        },
                    )
                )
            wizard.warehouse_line_ids = warehouse_commands

            quant_groups = (
                self.env["stock.quant"]
                .sudo()
                .read_group(
                    [
                        ("product_id", "=", product.id),
                        ("company_id", "=", company.id),
                        ("location_id.usage", "=", "internal"),
                    ],
                    ["quantity:sum", "reserved_quantity:sum", "location_id"],
                    ["location_id"],
                    orderby="location_id",
                )
            )
            location_commands = []
            for group in quant_groups:
                location_id = group.get("location_id") and group["location_id"][0]
                if not location_id:
                    continue
                qty_on_hand = group.get("quantity", 0.0)
                qty_reserved = group.get("reserved_quantity", 0.0)
                qty_available = qty_on_hand - qty_reserved
                qty_forecasted = (
                    product.with_context(location=location_id, company_id=company.id)
                    .sudo()
                    .virtual_available
                )
                location_commands.append(
                    (
                        0,
                        0,
                        {
                            "location_id": location_id,
                            "qty_on_hand": _to_line_uom(qty_on_hand),
                            "qty_reserved": _to_line_uom(qty_reserved),
                            "qty_available": _to_line_uom(qty_available),
                            "qty_forecasted": _to_line_uom(qty_forecasted),
                        },
                    )
                )
            wizard.location_line_ids = location_commands

            if not sale_line.order_id.partner_id:
                continue

            history_domain = [
                ("product_id", "=", product.id),
                ("order_id.partner_id", "=", sale_line.order_id.partner_id.id),
                ("order_id.state", "in", ("sale", "done")),
            ]
            if sale_line.order_id.date_order:
                history_domain.append(
                    ("order_id.date_order", "<", sale_line.order_id.date_order)
                )
            if sale_line.id:
                history_domain.append(("id", "!=", sale_line.id))
            history_lines = self.env["sale.order.line"].search(
                history_domain, order="id desc", limit=20
            )
            history_commands = []
            for line in history_lines:
                history_commands.append(
                    (
                        0,
                        0,
                        {
                            "order_id": line.order_id.id,
                            "order_date": line.order_id.date_order,
                            "qty": line.product_uom_qty,
                            "uom_id": line.product_uom.id,
                            "price_subtotal": line.price_subtotal,
                        },
                    )
                )
            wizard.customer_product_history_ids = history_commands


class SalesProductAvailabilityWarehouseLine(models.TransientModel):
    _name = "flewstack_sales_product_availability_warehouse_line"
    _description = "Sales Product Availability Warehouse Line"
    _order = "warehouse_id"

    wizard_id = fields.Many2one(
        "flewstack_sales_product_availability", required=True, ondelete="cascade"
    )
    warehouse_id = fields.Many2one("stock.warehouse", required=True)
    qty_on_hand = fields.Float(string="On Hand", digits="Product Unit")
    qty_reserved = fields.Float(string="Reserved", digits="Product Unit")
    qty_available = fields.Float(string="Available", digits="Product Unit")
    qty_forecasted = fields.Float(string="Forecasted", digits="Product Unit")


class SalesProductAvailabilityLocationLine(models.TransientModel):
    _name = "flewstack_sales_product_availability_location_line"
    _description = "Sales Product Availability Location Line"
    _order = "location_id"

    wizard_id = fields.Many2one(
        "flewstack_sales_product_availability", required=True, ondelete="cascade"
    )
    location_id = fields.Many2one("stock.location", required=True)
    qty_on_hand = fields.Float(string="On Hand", digits="Product Unit")
    qty_reserved = fields.Float(string="Reserved", digits="Product Unit")
    qty_available = fields.Float(string="Available", digits="Product Unit")
    qty_forecasted = fields.Float(string="Forecasted", digits="Product Unit")


class SalesProductAvailabilityHistoryLine(models.TransientModel):
    _name = "flewstack_sales_product_availability_history_line"
    _description = "Sales Product Availability Customer History Line"
    _order = "order_date desc, id desc"

    wizard_id = fields.Many2one(
        "flewstack_sales_product_availability", required=True, ondelete="cascade"
    )
    order_id = fields.Many2one("sale.order", required=True)
    order_date = fields.Datetime(string="Order Date", required=True)
    qty = fields.Float(string="Quantity", digits="Product Unit")
    uom_id = fields.Many2one("uom.uom", string="UoM")
    price_subtotal = fields.Monetary(string="Subtotal", currency_field="currency_id")
    currency_id = fields.Many2one(related="order_id.currency_id", readonly=True)
