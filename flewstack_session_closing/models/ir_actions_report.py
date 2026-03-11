from odoo import _, models
from odoo.exceptions import UserError


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    _INVOICE_REPORT_REFS = ("account.report_invoice", "account.report_invoice_with_payments")
    _INVOICE_MOVE_TYPES = {
        "out_invoice",
        "out_refund",
        "out_receipt",
        "in_invoice",
        "in_refund",
        "in_receipt",
    }

    def _is_invoice_move(self, move):
        return move.move_type in self._INVOICE_MOVE_TYPES

    def _linked_invoice_moves_from_entry(self, move):
        invoices = self.env["account.move"]

        # Reversal relation (entry generated from invoice reversal flow or vice versa).
        invoices |= move.reversed_entry_id.filtered(self._is_invoice_move)
        invoices |= move.reversal_move_id.filtered(self._is_invoice_move)

        # Payment relation (if this journal entry is a payment move).
        if "payment_id" in move._fields and move.payment_id:
            payment = move.payment_id
            if "reconciled_invoice_ids" in payment._fields:
                invoices |= payment.reconciled_invoice_ids.filtered(self._is_invoice_move)
            elif hasattr(payment, "_get_reconciled_invoices"):
                invoices |= payment._get_reconciled_invoices().filtered(self._is_invoice_move)

        # Reconciliation relation (common between entry and invoice receivable/payable lines).
        for line in move.line_ids:
            invoices |= line.matched_debit_ids.mapped("credit_move_id.move_id").filtered(self._is_invoice_move)
            invoices |= line.matched_credit_ids.mapped("debit_move_id.move_id").filtered(self._is_invoice_move)
            if "full_reconcile_id" in line._fields and line.full_reconcile_id:
                invoices |= line.full_reconcile_id.reconciled_line_ids.mapped("move_id").filtered(
                    self._is_invoice_move
                )

        return invoices

    def _resolve_invoice_report_res_ids(self, res_ids):
        moves = self.env["account.move"].browse(res_ids).exists()
        invoice_moves = self.env["account.move"]
        unresolved_entries = self.env["account.move"]

        for move in moves:
            if self._is_invoice_move(move):
                invoice_moves |= move
                continue
            if move.move_type != "entry":
                continue

            linked = self._linked_invoice_moves_from_entry(move)
            if linked:
                invoice_moves |= linked
            else:
                unresolved_entries |= move

        if unresolved_entries:
            raise UserError(
                _(
                    "No related invoice was found for: %(moves)s. "
                    "Open the invoice directly, or ensure this entry is reconciled with an invoice."
                )
                % {"moves": ", ".join(unresolved_entries.mapped("display_name"))}
            )

        return invoice_moves.ids

    def _pre_render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        if report_ref in self._INVOICE_REPORT_REFS and res_ids:
            resolved_res_ids = self._resolve_invoice_report_res_ids(res_ids)
            if resolved_res_ids:
                return super()._pre_render_qweb_pdf(report_ref, res_ids=resolved_res_ids, data=data)
        return super()._pre_render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
