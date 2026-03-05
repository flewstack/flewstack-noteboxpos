# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class SaleReport(models.Model):
    _inherit = "sale.report"

    brand_id = fields.Many2one("product.brand", string="Brand", readonly=True)

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res["brand_id"] = "t.brand_id"
        return res

    def _group_by_sale(self):
        return super()._group_by_sale() + ", t.brand_id"
