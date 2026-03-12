from odoo import _, Command, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero


class StockReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    return_location_id = fields.Many2one(
        "stock.location",
        string="Return To",
        domain="[('usage', '!=', 'view'), ('company_id', 'in', [False, wizard_id.company_id])]",
        help="Destination location for this return line.",
    )


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    apply_all_return_location_id = fields.Many2one(
        "stock.location",
        string="Apply Location To All Lines",
        domain="[('usage', '!=', 'view'), ('company_id', 'in', [False, company_id])]",
        help="Select a location here to push it to every return line in this wizard.",
    )

    def _sanitize_copied_values(self, model, values):
        clean_values = dict(values)
        for field_name in list(clean_values):
            field = model._fields.get(field_name)
            if (
                not field
                or field.related
                or field.type in {"one2many", "many2many"}
                or (field.compute and not field.inverse)
            ):
                clean_values.pop(field_name, None)
        return clean_values

    def _is_zero_return_quantity(self, line):
        rounding = line.uom_id.rounding if line.uom_id else line.product_id.uom_id.rounding
        return float_is_zero(line.quantity, precision_rounding=rounding)

    def _get_lines_to_return(self):
        self.ensure_one()
        return self.product_return_moves.filtered(lambda line: not self._is_zero_return_quantity(line))

    def _get_default_return_location(self, picking=None):
        self.ensure_one()
        picking = picking or self.picking_id
        if not picking:
            return self.env["stock.location"]
        vals = super()._prepare_picking_default_values_based_on(picking)
        return self.env["stock.location"].browse(vals.get("location_dest_id"))

    def _get_return_location_for_line(self, line):
        self.ensure_one()
        return line.return_location_id or self._get_default_return_location()

    def _get_distinct_return_locations(self, lines=None):
        self.ensure_one()
        lines = lines or self._get_lines_to_return()
        locations = self.env["stock.location"]
        for line in lines:
            locations |= self._get_return_location_for_line(line)
        return locations

    def _prepare_stock_return_picking_line_vals_from_move(self, stock_move):
        vals = super()._prepare_stock_return_picking_line_vals_from_move(stock_move)
        default_location = self._get_default_return_location()
        if default_location:
            vals["return_location_id"] = default_location.id
        return vals

    def _apply_all_return_location(self):
        for wizard in self:
            if wizard.apply_all_return_location_id:
                wizard.product_return_moves.return_location_id = wizard.apply_all_return_location_id

    @api.onchange("apply_all_return_location_id")
    def _onchange_apply_all_return_location_id(self):
        self._apply_all_return_location()

    def _prepare_picking_default_values_based_on(self, picking):
        vals = super()._prepare_picking_default_values_based_on(picking)
        forced_location_id = self.env.context.get("force_return_location_id")
        if forced_location_id:
            vals["location_dest_id"] = forced_location_id
            return vals

        selected_locations = self._get_distinct_return_locations()
        if len(selected_locations) == 1:
            vals["location_dest_id"] = selected_locations.id
        return vals

    def _action_open_return_pickings(self, pickings):
        if len(pickings) == 1:
            return {
                "name": _("Returned Picking"),
                "view_mode": "form",
                "res_model": "stock.picking",
                "res_id": pickings.id,
                "type": "ir.actions.act_window",
                "context": self.env.context,
            }
        return {
            "name": _("Returned Pickings"),
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "view_mode": "list,form",
            "domain": [("id", "in", pickings.ids)],
            "context": self.env.context,
        }

    def _create_split_wizard(self, lines):
        self.ensure_one()
        wizard_vals = self._sanitize_copied_values(self, self.copy_data()[0])
        wizard = self.create(wizard_vals)
        wizard.product_return_moves.unlink()
        wizard.write({
            "product_return_moves": [
                Command.create(
                    self._sanitize_copied_values(line, line.copy_data()[0])
                )
                for line in lines
            ]
        })
        return wizard

    def action_create_returns(self):
        self.ensure_one()
        if self.env.context.get("skip_return_location_split"):
            return super().action_create_returns()

        self._apply_all_return_location()
        lines_to_return = self._get_lines_to_return()
        selected_locations = self._get_distinct_return_locations(lines_to_return)
        if len(selected_locations) <= 1:
            return super().action_create_returns()

        created_pickings = self.env["stock.picking"]
        for location in selected_locations:
            location_lines = lines_to_return.filtered(
                lambda line: self._get_return_location_for_line(line) == location
            )
            wizard = self._create_split_wizard(location_lines)
            action = wizard.with_context(
                skip_return_location_split=True,
                force_return_location_id=location.id,
            ).action_create_returns()
            if action.get("res_id"):
                created_pickings |= self.env["stock.picking"].browse(action["res_id"])

        if not created_pickings:
            raise UserError(_("Please specify at least one non-zero quantity."))
        return self._action_open_return_pickings(created_pickings)

    def action_create_exchanges(self):
        self.ensure_one()
        self._apply_all_return_location()
        if len(self._get_distinct_return_locations()) > 1:
            raise UserError(
                _("Return for Exchange supports only one return destination location at a time.")
            )
        return super().action_create_exchanges()
