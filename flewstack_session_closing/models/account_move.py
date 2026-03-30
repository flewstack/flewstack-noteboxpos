from odoo import _, models
from odoo.exceptions import UserError
from odoo.addons.point_of_sale.models.account_move import AccountMove as PosAccountMove


class AccountMove(models.Model):
    _inherit = 'account.move'

    def button_draft(self):
        blocked_orders = self.sudo().pos_order_ids.filtered(
            lambda order: order.session_id.state not in ('closed', 'handed_over')
        )
        if blocked_orders:
            self.env.user._bus_send("simple_notification", {
                'type': 'danger',
                'message': _(
                    "You can't reset this invoice to draft because the POS session is still open.\n"
                    "Please close the ongoing session first, then try again."
                ),
                'sticky': True,
            })
            return False
        return super(PosAccountMove, self).button_draft()

    def action_open_transfer_cash(self):
        self.ensure_one()
        if self.state != 'posted':
            raise UserError(_("Only posted journal entries can be transferred."))
        if self.journal_id.type != 'cash':
            raise UserError(_("Transfer Cash is only available for cash journals."))
        return {
            'name': _('Transfer Cash'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.transfer.cash.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_id': self.id,
            },
        }
