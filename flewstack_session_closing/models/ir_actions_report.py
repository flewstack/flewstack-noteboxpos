from odoo import models
from odoo.addons.base.models.ir_actions_report import IrActionsReport as BaseIrActionsReport


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _pre_render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        if report_ref in ("account.report_invoice", "account.report_invoice_with_payments") and res_ids:
            moves = self.env["account.move"].browse(res_ids).exists()
            if moves and any(move.move_type == "entry" for move in moves):
                # Allow invoice templates to render for journal entries selected from account.move.
                return BaseIrActionsReport._pre_render_qweb_pdf(
                    self, report_ref, res_ids=res_ids, data=data
                )
        return super()._pre_render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
