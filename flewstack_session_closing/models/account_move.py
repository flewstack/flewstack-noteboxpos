from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

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
