# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


class ProductBrand(models.Model):
    _name = "product.brand"
    _description = "Product Brand"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    description = fields.Text()
    logo = fields.Binary(string="Logo", attachment=True)
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        string="Currency",
        required=True,
    )
    product_template_ids = fields.One2many(
        "product.template",
        "brand_id",
        string="Products",
    )
    product_count = fields.Integer(
        string="Number of Products",
        compute="_compute_product_count",
        store=True,
    )
    sale_order_line_ids = fields.Many2many(
        "sale.order.line",
        string="Sales Lines",
        compute="_compute_sales_data",
        readonly=True,
    )
    sale_total = fields.Monetary(
        string="Total Sales",
        currency_field="currency_id",
        compute="_compute_sales_data",
        store=False,
        readonly=True,
    )
    pos_order_line_ids = fields.Many2many(
        "pos.order.line",
        string="POS Lines",
        compute="_compute_sales_data",
        readonly=True,
    )
    pos_total = fields.Monetary(
        string="Total POS Sales",
        currency_field="currency_id",
        compute="_compute_sales_data",
        store=False,
        readonly=True,
    )
    purchase_order_line_ids = fields.Many2many(
        "purchase.order.line",
        string="Purchase Lines",
        compute="_compute_purchase_data",
        readonly=True,
    )
    purchase_total = fields.Monetary(
        string="Total Purchases",
        currency_field="currency_id",
        compute="_compute_purchase_data",
        store=False,
        readonly=True,
    )
    stock_quant_ids = fields.Many2many(
        "stock.quant",
        string="Stock Availability",
        compute="_compute_stock_quant_ids",
        readonly=True,
    )

    _sql_constraints = [
        ("name_unique", "unique(name)", _("A brand with this name already exists.")),
    ]

    @api.depends("product_template_ids")
    def _compute_product_count(self):
        for brand in self:
            brand.product_count = len(brand.product_template_ids)

    def _compute_sales_data(self):
        SaleLine = self.env["sale.order.line"]
        PosLine = self.env["pos.order.line"]
        for brand in self:
            sale_domain = [
                ("product_id.product_tmpl_id.brand_id", "=", brand.id),
                ("order_id.state", "in", ["sale", "done"]),
            ]
            pos_domain = [
                ("product_id.product_tmpl_id.brand_id", "=", brand.id),
                ("order_id.state", "in", ["paid", "invoiced", "done"]),
            ]
            sale_lines = SaleLine.search(sale_domain)
            pos_lines = PosLine.search(pos_domain)
            brand.sale_order_line_ids = sale_lines
            brand.pos_order_line_ids = pos_lines
            brand.sale_total = sum(sale_lines.mapped("price_total"))
            brand.pos_total = sum(pos_lines.mapped("price_subtotal_incl"))

    def _compute_purchase_data(self):
        PurchaseLine = self.env["purchase.order.line"]
        for brand in self:
            purchase_domain = [
                ("product_id.product_tmpl_id.brand_id", "=", brand.id),
                ("order_id.state", "in", ["purchase", "done"]),
            ]
            purchase_lines = PurchaseLine.search(purchase_domain)
            brand.purchase_order_line_ids = purchase_lines
            brand.purchase_total = sum(purchase_lines.mapped("price_total"))

    def _compute_stock_quant_ids(self):
        Quant = self.env["stock.quant"]
        for brand in self:
            quant_domain = [("product_id.product_tmpl_id.brand_id", "=", brand.id)]
            brand.stock_quant_ids = Quant.search(quant_domain)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    brand_id = fields.Many2one(
        "product.brand",
        string="Brand",
        ondelete="set null",
    )


class ProductProduct(models.Model):
    _inherit = "product.product"

    brand_id = fields.Many2one(
        related="product_tmpl_id.brand_id",
        store=True,
        readonly=False,
    )
