# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def action_view_flewstack_sales_product_availability(self):
        """Open the Flewstack sales product availability popup for this line."""
        self.ensure_one()
        if not self._origin.id:
            raise UserError(_("Save the sales order first, then check line availability."))
        if self.display_type or not self.product_id or not self.is_storable:
            raise UserError(_("Select a storable product line to check availability."))

        wizard = self.env["flewstack_sales_product_availability"].create(
            {"sale_line_id": self._origin.id}
        )
        wizard._fill_availability_lines()

        view = self.env.ref(
            "flewstack_sales_product_availability.flewstack_sales_product_availability_view_form"
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Product Availability"),
            "res_model": "flewstack_sales_product_availability",
            "view_mode": "form",
            "views": [(view.id, "form")],
            "target": "new",
            "res_id": wizard.id,
        }
