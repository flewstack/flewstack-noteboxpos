# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import format_amount


class ProductTemplate(models.Model):
    _inherit = "product.template"

    flewstack_average_cost = fields.Monetary(
        string="Average Cost",
        currency_field="currency_id",
        compute="_compute_flewstack_average_cost",
        store=True,
        readonly=True,
        help="Shows the current average cost pulled from the product cost.",
    )
    flewstack_threshold = fields.Monetary(
        string="Threshold",
        currency_field="currency_id",
        store=True,
        help="Defaulted to the average cost. Used to block excessive discounts in the POS.",
    )
    origin_id = fields.Many2one(
        "res.country",
        string="Origin",
        help="Country of origin used to control POS cost display.",
    )
    flewstack_is_origin_jordan = fields.Boolean(
        string="Origin is Jordan",
        compute="_compute_flewstack_is_origin_jordan",
        store=True,
    )

    @api.depends("product_variant_ids.standard_price")
    def _compute_flewstack_average_cost(self):
        for product in self:
            # Use the first variant cost (typical POS setup) or 0 when missing.
            variant = product.product_variant_ids[:1]
            product.flewstack_average_cost = variant.standard_price if variant else 0.0

    @api.onchange("flewstack_threshold")
    def _onchange_flewstack_threshold(self):
        for product in self:
            if (
                product.flewstack_threshold
                and product.flewstack_average_cost
                and product.flewstack_threshold < product.flewstack_average_cost
            ):
                formatted_cost = format_amount(
                    self.env, product.flewstack_average_cost, product.currency_id
                )
                return {
                    "warning": {
                        "title": _("Threshold Below Cost"),
                        "message": _(
                            "The threshold is lower than the current average cost (%s)."
                        )
                        % formatted_cost,
                    }
                }

    @api.depends("origin_id")
    def _compute_flewstack_is_origin_jordan(self):
        for product in self:
            country = product.origin_id
            country_code = (
                country.code or getattr(country, "country_code", None) if country else None
            )
            product.flewstack_is_origin_jordan = country_code == "JO"

    @api.constrains("flewstack_threshold")
    def _check_flewstack_threshold(self):
        for product in self:
            if product.flewstack_threshold is not None and product.flewstack_threshold < 0:
                raise ValidationError(_("The threshold cannot be negative."))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record, vals in zip(records, vals_list):
            if "flewstack_threshold" not in vals:
                record.flewstack_threshold = record.flewstack_average_cost
        return records

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        for field_name in [
            "flewstack_threshold",
            "flewstack_average_cost",
            "origin_id",
            "flewstack_is_origin_jordan",
        ]:
            if field_name not in fields_list:
                fields_list.append(field_name)
        return fields_list


class ProductProduct(models.Model):
    _inherit = "product.product"

    flewstack_average_cost = fields.Monetary(
        related="product_tmpl_id.flewstack_average_cost",
        currency_field="currency_id",
        readonly=True,
        store=True,
    )
    flewstack_threshold = fields.Monetary(
        related="product_tmpl_id.flewstack_threshold",
        currency_field="currency_id",
        readonly=False,
        store=True,
    )
    origin_id = fields.Many2one(
        related="product_tmpl_id.origin_id",
        string="Origin",
        store=True,
        readonly=False,
    )
    flewstack_is_origin_jordan = fields.Boolean(
        related="product_tmpl_id.flewstack_is_origin_jordan",
        store=True,
        readonly=True,
    )

    @api.model
    def _load_pos_data_fields(self, config):
        fields_list = super()._load_pos_data_fields(config)
        for field_name in [
            "flewstack_threshold",
            "flewstack_average_cost",
            "origin_id",
            "flewstack_is_origin_jordan",
        ]:
            if field_name not in fields_list:
                fields_list.append(field_name)
        return fields_list
