# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    flewstack_customer_history_ids = fields.Many2many(
        "sale.order",
        compute="_compute_flewstack_customer_history",
        string="Customer History",
    )

    @api.depends("partner_id", "date_order")
    def _compute_flewstack_customer_history(self):
        for order in self:
            if not order.partner_id:
                order.flewstack_customer_history_ids = [(5, 0, 0)]
                continue
            domain = [
                ("partner_id", "=", order.partner_id.id),
                ("state", "in", ("sale", "done")),
            ]
            if order.date_order:
                domain.append(("date_order", "<", order.date_order))
            if order.id:
                domain.append(("id", "!=", order.id))
            orders = self.env["sale.order"].search(domain, order="date_order desc, id desc")
            order.flewstack_customer_history_ids = orders
