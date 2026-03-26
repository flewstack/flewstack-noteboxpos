import base64
import io
from collections import defaultdict

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import date_utils

import xlsxwriter


class FlewstackTaxReportInvoicesWizard(models.TransientModel):
    _name = "flewstack.tax.report.invoices.wizard"
    _description = "Tax Report Invoices Export Wizard"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(
        string="From Date",
        required=True,
        default=lambda self: date_utils.start_of(fields.Date.context_today(self), "month"),
    )
    date_to = fields.Date(
        string="To Date",
        required=True,
        default=fields.Date.context_today,
    )
    move_state = fields.Selection(
        [
            ("posted", "Posted Entries"),
            ("all", "All Entries"),
        ],
        string="Entries",
        required=True,
        default="posted",
    )
    report_file = fields.Binary(string="Report File", readonly=True)
    report_filename = fields.Char(string="File Name", readonly=True)
    is_exported = fields.Boolean(string="Exported", readonly=True, default=False)

    def action_export_xlsx(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("The start date must be earlier than or equal to the end date."))

        payload = self._build_report_payload()
        if not payload["document_rows"]:
            raise UserError(_("No taxed sales invoices or journal entries were found for the selected filters."))

        xlsx_content = self._generate_xlsx(payload)
        filename = "tax_report_invoices_%s_%s.xlsx" % (self.date_from, self.date_to)
        self.write({
            "report_file": base64.b64encode(xlsx_content),
            "report_filename": filename,
            "is_exported": True,
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "target": "new",
            "res_id": self.id,
        }

    def action_back(self):
        self.ensure_one()
        self.write({"is_exported": False})
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "target": "new",
            "res_id": self.id,
        }

    def _build_report_payload(self):
        analytics_map = defaultdict(lambda: {
            "tax_label": "",
            "untaxed": 0.0,
            "tax_amount": 0.0,
            "total": 0.0,
        })
        document_rows = []
        grand_totals = {
            "untaxed": 0.0,
            "tax_amount": 0.0,
            "total": 0.0,
        }

        moves = self.env["account.move"].search(self._get_move_domain())
        moves = sorted(moves, key=lambda move: (
            move.invoice_date or move.date or fields.Date.context_today(self),
            move.name or "",
            move.id,
        ))

        for move in moves:
            taxable_lines = self._get_taxable_lines(move)
            if not taxable_lines:
                continue

            grouped_lines = defaultdict(lambda: {
                "tax_label": "",
                "untaxed": 0.0,
                "tax_amount": 0.0,
                "total": 0.0,
            })
            move_totals = {
                "untaxed": 0.0,
                "tax_amount": 0.0,
                "total": 0.0,
            }

            for line in taxable_lines:
                line_values = self._get_line_amounts(line)
                signature_key = tuple(self._get_tax_signature_parts(line.tax_ids))
                group = grouped_lines[signature_key]
                if not group["tax_label"]:
                    group["tax_label"] = self._format_tax_signature(line.tax_ids)
                group["untaxed"] += line_values["untaxed"]
                group["tax_amount"] += line_values["tax_amount"]
                group["total"] += line_values["total"]

                move_totals["untaxed"] += line_values["untaxed"]
                move_totals["tax_amount"] += line_values["tax_amount"]
                move_totals["total"] += line_values["total"]

                for tax_item in line_values["analytics"]:
                    analytics_row = analytics_map[tax_item["tax"].id]
                    analytics_row["tax_label"] = self._format_tax_label(tax_item["tax"])
                    analytics_row["untaxed"] += tax_item["untaxed"]
                    analytics_row["tax_amount"] += tax_item["tax_amount"]
                    analytics_row["total"] += tax_item["untaxed"] + tax_item["tax_amount"]

            grand_totals["untaxed"] += move_totals["untaxed"]
            grand_totals["tax_amount"] += move_totals["tax_amount"]
            grand_totals["total"] += move_totals["total"]

            move_row = self._prepare_move_row(move)
            sorted_groups = sorted(grouped_lines.values(), key=lambda values: values["tax_label"])
            if len(sorted_groups) == 1:
                group = sorted_groups[0]
                document_rows.append({
                    **move_row,
                    "row_type": "single",
                    "untaxed": group["untaxed"],
                    "tax_amount": group["tax_amount"],
                    "tax_label": group["tax_label"],
                    "total": group["total"],
                })
                continue

            document_rows.append({
                **move_row,
                "row_type": "header",
                "untaxed": move_totals["untaxed"],
                "tax_amount": move_totals["tax_amount"],
                "tax_label": _("Multiple Tax Rates"),
                "total": move_totals["total"],
            })
            for group in sorted_groups:
                document_rows.append({
                    "invoice_number": "",
                    "invoice_date": False,
                    "customer": "",
                    "row_type": "group",
                    "untaxed": group["untaxed"],
                    "tax_amount": group["tax_amount"],
                    "tax_label": group["tax_label"],
                    "total": group["total"],
                })

        analytics_rows = sorted(analytics_map.values(), key=lambda values: values["tax_label"])
        return {
            "document_rows": document_rows,
            "analytics_rows": analytics_rows,
            "grand_totals": grand_totals,
            "analytics_totals": {
                "untaxed": sum(row["untaxed"] for row in analytics_rows),
                "tax_amount": sum(row["tax_amount"] for row in analytics_rows),
                "total": sum(row["total"] for row in analytics_rows),
            },
        }

    def _generate_xlsx(self, payload):
        output = io.BytesIO()
        with xlsxwriter.Workbook(output, {"in_memory": True}) as workbook:
            self._write_documents_sheet(workbook, payload)
            self._write_analytics_sheet(workbook, payload)
        return output.getvalue()

    def _write_documents_sheet(self, workbook, payload):
        sheet = workbook.add_worksheet(_("Invoices"))
        sheet.freeze_panes(3, 0)
        sheet.set_column("A:A", 22)
        sheet.set_column("B:B", 14)
        sheet.set_column("C:C", 28)
        sheet.set_column("D:F", 18)
        sheet.set_column("G:G", 28)

        title_format = workbook.add_format({
            "bold": True,
            "font_size": 14,
            "align": "center",
            "valign": "vcenter",
        })
        note_format = workbook.add_format({
            "italic": True,
            "font_color": "#666666",
        })
        header_format = workbook.add_format({
            "bold": True,
            "bg_color": "#D9E1F2",
            "border": 1,
            "align": "center",
        })
        text_format = workbook.add_format({"border": 1})
        group_text_format = workbook.add_format({"border": 1, "bold": True, "bg_color": "#F2F2F2"})
        subgroup_text_format = workbook.add_format({"border": 1, "indent": 1})
        amount_format = workbook.add_format({"border": 1, "num_format": "#,##0.00"})
        group_amount_format = workbook.add_format({
            "border": 1,
            "bold": True,
            "bg_color": "#F2F2F2",
            "num_format": "#,##0.00",
        })
        total_label_format = workbook.add_format({
            "bold": True,
            "top": 2,
            "border": 1,
        })
        total_amount_format = workbook.add_format({
            "bold": True,
            "top": 2,
            "border": 1,
            "num_format": "#,##0.00",
        })

        sheet.merge_range(0, 0, 0, 6, _("Taxed Invoices and Journal Entries"), title_format)
        sheet.merge_range(
            1,
            0,
            1,
            6,
            _("Amounts are shown in company currency: %s") % self.company_id.currency_id.name,
            note_format,
        )

        headers = [
            _("Invoice Number"),
            _("Invoice Date"),
            _("Customer"),
            _("Price before Tax"),
            _("Tax Amount"),
            _("Tax Applied"),
            _("Price After Tax"),
        ]
        for col, header in enumerate(headers):
            sheet.write(2, col, header, header_format)

        row_index = 3
        for row in payload["document_rows"]:
            is_group_header = row["row_type"] == "header"
            is_group_line = row["row_type"] == "group"
            text_cell_format = group_text_format if is_group_header else subgroup_text_format if is_group_line else text_format
            amount_cell_format = group_amount_format if is_group_header else amount_format

            sheet.write(row_index, 0, row["invoice_number"], text_cell_format)
            sheet.write(row_index, 1, str(row["invoice_date"] or ""), text_cell_format)
            sheet.write(row_index, 2, row["customer"], text_cell_format)
            sheet.write_number(row_index, 3, row["untaxed"], amount_cell_format)
            sheet.write_number(row_index, 4, row["tax_amount"], amount_cell_format)
            sheet.write(row_index, 5, row["tax_label"], text_cell_format)
            sheet.write_number(row_index, 6, row["total"], amount_cell_format)
            row_index += 1

        sheet.write(row_index, 0, _("Grand Total"), total_label_format)
        sheet.write_blank(row_index, 1, "", total_label_format)
        sheet.write_blank(row_index, 2, "", total_label_format)
        sheet.write_number(row_index, 3, payload["grand_totals"]["untaxed"], total_amount_format)
        sheet.write_number(row_index, 4, payload["grand_totals"]["tax_amount"], total_amount_format)
        sheet.write_blank(row_index, 5, "", total_label_format)
        sheet.write_number(row_index, 6, payload["grand_totals"]["total"], total_amount_format)

    def _write_analytics_sheet(self, workbook, payload):
        sheet = workbook.add_worksheet(_("Tax Analytics"))
        sheet.freeze_panes(3, 0)
        sheet.set_column("A:A", 30)
        sheet.set_column("B:D", 18)

        title_format = workbook.add_format({
            "bold": True,
            "font_size": 14,
            "align": "center",
            "valign": "vcenter",
        })
        note_format = workbook.add_format({
            "italic": True,
            "font_color": "#666666",
        })
        header_format = workbook.add_format({
            "bold": True,
            "bg_color": "#FCE4D6",
            "border": 1,
            "align": "center",
        })
        text_format = workbook.add_format({"border": 1})
        amount_format = workbook.add_format({"border": 1, "num_format": "#,##0.00"})
        total_label_format = workbook.add_format({
            "bold": True,
            "top": 2,
            "border": 1,
        })
        total_amount_format = workbook.add_format({
            "bold": True,
            "top": 2,
            "border": 1,
            "num_format": "#,##0.00",
        })

        sheet.merge_range(0, 0, 0, 3, _("Tax Analytics by Tax Type"), title_format)
        sheet.merge_range(
            1,
            0,
            1,
            3,
            _("Lines with multiple taxes contribute to each applicable tax type."),
            note_format,
        )

        headers = [
            _("Tax Type"),
            _("Total Sale"),
            _("Tax Amount"),
            _("Summation"),
        ]
        for col, header in enumerate(headers):
            sheet.write(2, col, header, header_format)

        row_index = 3
        for row in payload["analytics_rows"]:
            sheet.write(row_index, 0, row["tax_label"], text_format)
            sheet.write_number(row_index, 1, row["untaxed"], amount_format)
            sheet.write_number(row_index, 2, row["tax_amount"], amount_format)
            sheet.write_number(row_index, 3, row["total"], amount_format)
            row_index += 1

        sheet.write(row_index, 0, _("Grand Total"), total_label_format)
        sheet.write_number(row_index, 1, payload["analytics_totals"]["untaxed"], total_amount_format)
        sheet.write_number(row_index, 2, payload["analytics_totals"]["tax_amount"], total_amount_format)
        sheet.write_number(row_index, 3, payload["analytics_totals"]["total"], total_amount_format)

    def _get_move_domain(self):
        domain = [
            ("company_id", "=", self.company_id.id),
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
            ("move_type", "in", ["out_invoice", "out_refund", "out_receipt", "entry"]),
        ]
        if self.move_state == "posted":
            domain.append(("state", "=", "posted"))
        return domain

    def _get_taxable_lines(self, move):
        return move.line_ids.filtered(lambda line: line.display_type == "product" and line.tax_ids and not line.tax_line_id)

    def _prepare_move_row(self, move):
        return {
            "invoice_number": move.name if move.name and move.name != "/" else move.ref or _("Draft"),
            "invoice_date": move.invoice_date or move.date,
            "customer": move.partner_id.display_name or "",
        }

    def _get_line_amounts(self, line):
        account_tax = self.env["account.tax"]
        move = line.move_id
        sign = -1 if move.move_type == "out_refund" else 1
        base_line = move._prepare_product_base_line_for_taxes_computation(line)
        account_tax._add_tax_details_in_base_line(base_line, move.company_id)
        account_tax._round_base_lines_tax_details([base_line], move.company_id)

        tax_details = base_line["tax_details"]
        untaxed = sign * tax_details.get("total_excluded", tax_details["raw_total_excluded"])
        total = sign * tax_details.get("total_included", tax_details["raw_total_included"])
        analytics = []
        tax_amount = 0.0
        for tax_data in tax_details["taxes_data"]:
            rounded_base = sign * tax_data.get("base_amount", tax_data["raw_base_amount"])
            rounded_tax = sign * tax_data.get("tax_amount", tax_data["raw_tax_amount"])
            tax_amount += rounded_tax
            analytics.append({
                "tax": tax_data["tax"],
                "untaxed": rounded_base,
                "tax_amount": rounded_tax,
            })
        return {
            "untaxed": untaxed,
            "tax_amount": tax_amount,
            "total": total,
            "analytics": analytics,
        }

    def _format_tax_signature(self, taxes):
        return ", ".join(self._get_tax_signature_parts(taxes))

    def _get_tax_signature_parts(self, taxes):
        return [
            self._format_tax_label(tax)
            for tax in taxes.sorted(key=lambda tax: (tax.sequence, tax.id))
        ]

    def _format_tax_label(self, tax):
        rate = self._get_tax_rate_label(tax)
        return "%s [%s]" % (tax.display_name, rate)

    def _get_tax_rate_label(self, tax):
        if tax.amount_type == "percent":
            return "%s%%" % self._format_number(tax.amount)
        if tax.amount_type == "division":
            return _("%s%% division") % self._format_number(tax.amount)
        if tax.amount_type == "fixed":
            return _("%s fixed") % self._format_number(tax.amount)
        if tax.amount_type == "group":
            return _("Group")
        return _("Python")

    def _format_number(self, value):
        return ("%0.2f" % value).rstrip("0").rstrip(".")
