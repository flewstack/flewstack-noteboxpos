# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    company_currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Company Currency",
        store=False,
        readonly=True,
    )


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    company_currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Company Currency",
        store=False,
        readonly=True,
    )


class AccountMove(models.Model):
    _inherit = "account.move"

    company_currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Company Currency",
        store=False,
        readonly=True,
    )


class AccountPayment(models.Model):
    _inherit = "account.payment"

    company_currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Company Currency",
        store=False,
        readonly=True,
    )

    payment_currency_rate = fields.Float(
        string="Payment Currency Rate",
        compute="_compute_payment_currency_rate",
        inverse="_inverse_payment_currency_rate",
        digits=(12, 6),
        store=False,
    )

    payment_currency_rate_manual = fields.Float(
        string="Manual Exchange Rate",
        digits=(12, 6),
        copy=False,
        help="Optional override: 1 Company Currency = this many Payment Currency units.",
    )

    payment_amount_company_currency = fields.Monetary(
        string="Amount in Company Currency",
        currency_field="company_currency_id",
        compute="_compute_payment_amount_company_currency",
        store=False,
    )

    @api.depends("currency_id", "company_id", "date")
    def _compute_payment_currency_rate(self):
        Currency = self.env["res.currency"]
        for payment in self:
            manual_rate = payment.payment_currency_rate_manual
            if manual_rate:
                payment.payment_currency_rate = manual_rate
            elif payment.currency_id and payment.company_id:
                payment.payment_currency_rate = Currency._get_conversion_rate(
                    from_currency=payment.company_id.currency_id,
                    to_currency=payment.currency_id,
                    company=payment.company_id,
                    date=payment.date or fields.Date.context_today(payment),
                )
            else:
                payment.payment_currency_rate = 1.0

    def _inverse_payment_currency_rate(self):
        for payment in self:
            payment.payment_currency_rate_manual = payment.payment_currency_rate or 0.0

    @api.depends("amount", "currency_id", "company_id", "date")
    def _compute_payment_amount_company_currency(self):
        for payment in self:
            company_currency = payment.company_id.currency_id
            if payment.currency_id and company_currency:
                manual_rate = payment.payment_currency_rate_manual
                if manual_rate and manual_rate > 0 and payment.currency_id != company_currency:
                    payment.payment_amount_company_currency = payment.amount / manual_rate
                else:
                    payment.payment_amount_company_currency = payment.currency_id._convert(
                        payment.amount,
                        company_currency,
                        payment.company_id,
                        payment.date or fields.Date.context_today(payment),
                    )
            else:
                payment.payment_amount_company_currency = payment.amount

    @api.onchange("currency_id", "company_id", "date")
    def _onchange_reset_manual_rate(self):
        for payment in self:
            if payment.currency_id != payment.company_id.currency_id:
                payment.payment_currency_rate_manual = False
