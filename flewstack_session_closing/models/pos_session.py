from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PosSession(models.Model):
    _inherit = 'pos.session'

    state = fields.Selection(
        selection_add=[('handed_over', 'Handed Over')],
        ondelete={'handed_over': 'set default'},
    )
    handed_over_by_id = fields.Many2one('res.users', string='Handed Over By', readonly=True)
    handed_over_at = fields.Datetime(string='Handed Over At', readonly=True)
    handed_over_move_id = fields.Many2one('account.move', string='Hand Over Entry', readonly=True)
    handed_over_employee_id = fields.Many2one('hr.employee', string='Handed Over Employee', readonly=True)

    @api.constrains('config_id')
    def _check_pos_config(self):
        onboarding_creation = self.env.context.get('onboarding_creation', False)
        if onboarding_creation:
            return
        for session in self:
            if self.search_count([
                ('state', 'not in', ('closed', 'handed_over')),
                ('config_id', '=', session.config_id.id),
                ('rescue', '=', False),
            ]) > 1:
                raise ValidationError(_("Another session is already opened for this point of sale."))

    def _get_clear_cash_source_journal(self):
        self.ensure_one()
        if self.cash_journal_id:
            return self.cash_journal_id
        cash_payment_method = self.config_id.payment_method_ids.filtered('is_cash_count')[:1]
        return cash_payment_method.journal_id

    def action_open_clear_cash_auth(self):
        self.ensure_one()
        if self.state == 'handed_over':
            raise UserError(_("This session has already been handed over."))
        if self.state != 'closed':
            raise UserError(_("Clear Cash is only available after the session is Closed & Posted."))
        return {
            'name': _('Clear Cash Authentication'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.session.clear.cash.auth',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_session_id': self.id,
            },
        }

    def _log_clear_cash_activity(self, transfer_amount, expected_amount, difference_amount, move, employee, cash_received=None):
        self.ensure_one()
        currency = self.currency_id
        difference_label = _('No Difference')
        if difference_amount > 0:
            difference_label = _('Shortage')
        elif difference_amount < 0:
            difference_label = _('Overage')
        cash_received_line = ''
        if cash_received:
            cash_received_line = _("\nCash Received: %(cash_received)s") % {
                'cash_received': currency and currency.format(cash_received) or cash_received,
            }
        body = _(
            "Cash handed over to %(employee)s.\n"
            "Expected: %(expected)s\n"
            "Transferred: %(transfer)s%(cash_received_line)s\n"
            "Difference: %(difference)s (%(difference_label)s)\n"
            "Entry: %(move)s"
        ) % {
            'employee': employee.name,
            'expected': currency and currency.format(expected_amount) or expected_amount,
            'transfer': currency and currency.format(transfer_amount) or transfer_amount,
            'difference': currency and currency.format(difference_amount) or difference_amount,
            'difference_label': difference_label,
            'move': move.display_name if move else _('No journal entry'),
            'cash_received_line': cash_received_line,
        }
        self.message_post(body=body)
