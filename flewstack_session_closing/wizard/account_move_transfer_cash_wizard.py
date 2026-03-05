from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMoveTransferCashWizard(models.TransientModel):
    _name = 'account.move.transfer.cash.wizard'
    _description = 'Transfer Cash Between Journals'

    move_id = fields.Many2one('account.move', required=True, readonly=True)
    source_journal_id = fields.Many2one('account.journal', readonly=True)
    destination_journal_id = fields.Many2one(
        'account.journal',
        required=True,
        domain="[('type', '=', 'cash'), ('company_id', '=', company_id), ('id', '!=', source_journal_id)]",
    )
    company_id = fields.Many2one(related='move_id.company_id', readonly=True)
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)
    amount = fields.Monetary(string='Amount', readonly=True, compute='_compute_amount')

    @api.depends('move_id')
    def _compute_amount(self):
        for wizard in self:
            move = wizard.move_id
            amount = 0.0
            source_account = move.journal_id.default_account_id
            if source_account:
                balance = sum(move.line_ids.filtered(lambda l: l.account_id == source_account).mapped('balance'))
                if balance:
                    amount = abs(balance)
            if not amount:
                amount = sum(move.line_ids.mapped('debit'))
            wizard.amount = amount
            wizard.source_journal_id = move.journal_id

    def action_confirm(self):
        self.ensure_one()
        move = self.move_id
        if move.state != 'posted':
            raise UserError(_("Only posted journal entries can be transferred."))
        if move.journal_id.type != 'cash':
            raise UserError(_("Transfer Cash is only available for cash journals."))

        source_journal = move.journal_id
        destination_journal = self.destination_journal_id
        if not destination_journal:
            raise UserError(_("Please select a destination cash journal."))
        if not source_journal.default_account_id or not destination_journal.default_account_id:
            raise UserError(_("Both cash journals must have a default account."))
        if self.amount <= 0:
            raise UserError(_("The transfer amount must be positive."))

        transfer_move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': destination_journal.id,
            'date': fields.Date.context_today(self),
            'ref': _('Cash Transfer from %s') % source_journal.display_name,
            'line_ids': [
                (0, 0, {
                    'name': _('Cash transfer from %s') % source_journal.display_name,
                    'account_id': source_journal.default_account_id.id,
                    'credit': self.amount,
                    'debit': 0.0,
                }),
                (0, 0, {
                    'name': _('Cash received in %s') % destination_journal.display_name,
                    'account_id': destination_journal.default_account_id.id,
                    'debit': self.amount,
                    'credit': 0.0,
                }),
            ],
        })
        transfer_move.action_post()

        move.message_post(body=_('Cash transferred to %s via %s.') % (destination_journal.display_name, transfer_move.display_name))

        notify_user = source_journal.notify_user_id
        if notify_user:
            notify_user.sudo()._bus_send('simple_notification', {
                'type': 'success',
                'title': _('Cash Transfer Completed'),
                'message': _('%(amount)s transferred from %(source)s to %(destination)s.') % {
                    'amount': self.currency_id.format(self.amount),
                    'source': source_journal.display_name,
                    'destination': destination_journal.display_name,
                },
                'sticky': False,
            })

        return {'type': 'ir.actions.act_window_close'}
