# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools


class StockLandedCostProductReport(models.Model):
    _name = "stock.landed.cost.product.report"
    _description = "Landed Cost Product Summary"
    _auto = False
    _rec_name = "product_id"
    _order = "product_id"

    cost_id = fields.Many2one("stock.landed.cost", string="Landed Cost", readonly=True)
    product_id = fields.Many2one("product.product", string="Product", readonly=True)
    quantity = fields.Float(string="Quantity", readonly=True)
    original_value_total = fields.Monetary(
        string="Original Value Total",
        readonly=True,
        currency_field="currency_id",
    )
    new_value_total = fields.Monetary(
        string="New Value Total",
        readonly=True,
        currency_field="currency_id",
    )
    original_unit_cost = fields.Monetary(
        string="Original Unit Cost",
        compute="_compute_unit_costs",
        readonly=True,
        currency_field="currency_id",
    )
    new_unit_cost = fields.Monetary(
        string="New Unit Cost",
        compute="_compute_unit_costs",
        readonly=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)

    @api.depends("quantity", "original_value_total", "new_value_total")
    def _compute_unit_costs(self):
        for line in self:
            if line.quantity:
                line.original_unit_cost = line.original_value_total / line.quantity
                line.new_unit_cost = line.new_value_total / line.quantity
            else:
                line.original_unit_cost = 0.0
                line.new_unit_cost = 0.0

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    MIN(val.id) AS id,
                    val.cost_id AS cost_id,
                    val.product_id AS product_id,
                    SUM(val.quantity) AS quantity,
                    SUM(COALESCE(val.former_cost, 0.0)) AS original_value_total,
                    SUM(COALESCE(val.final_cost, 0.0)) AS new_value_total,
                    cost.company_id AS company_id,
                    company.currency_id AS currency_id
                FROM stock_valuation_adjustment_lines val
                JOIN stock_landed_cost cost ON cost.id = val.cost_id
                JOIN res_company company ON company.id = cost.company_id
                GROUP BY val.cost_id, val.product_id, cost.company_id, company.currency_id
            )
            """
        )


class StockLandedCost(models.Model):
    _inherit = "stock.landed.cost"

    landed_cost_product_count = fields.Integer(
        string="Landed Cost Products",
        compute="_compute_landed_cost_product_count",
    )

    @api.depends("valuation_adjustment_lines.product_id")
    def _compute_landed_cost_product_count(self):
        count_map = {cost_id: 0 for cost_id in self.ids}
        if self.ids:
            groups = self.env["stock.valuation.adjustment.lines"].read_group(
                [("cost_id", "in", self.ids)],
                ["product_id"],
                ["cost_id", "product_id"],
                lazy=False,
            )
            for group in groups:
                cost_id = group.get("cost_id") and group["cost_id"][0]
                if cost_id in count_map:
                    count_map[cost_id] += 1
        for cost in self:
            cost.landed_cost_product_count = count_map.get(cost.id, 0)

    def action_view_landed_cost_product_summary(self):
        self.ensure_one()
        action = self.env.ref(
            "stock_landed_cost_product_summary.action_stock_landed_cost_product_report"
        ).read()[0]
        action["domain"] = [("cost_id", "=", self.id)]
        action["context"] = dict(self.env.context, default_cost_id=self.id)
        return action
