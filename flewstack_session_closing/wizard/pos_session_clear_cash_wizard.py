from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PosSessionClearCashWizard(models.TransientModel):
    _name = 'pos.session.clear.cash.wizard'
    _description = 'POS Clear Cash Destination Journal'

    session_id = fields.Many2one('pos.session', required=True, readonly=True)
    employee_public_id = fields.Many2one('hr.employee.public', required=True, readonly=True)
    employee_id = fields.Many2one('hr.employee', compute='_compute_employee', readonly=True)
    currency_id = fields.Many2one(related='session_id.currency_id', readonly=True)
    source_journal_id = fields.Many2one('account.journal', string='Source Journal', compute='_compute_source_journal')
    destination_journal_id = fields.Many2one('account.journal', string='Destination Journal', compute='_compute_destination_journal')
    expected_amount = fields.Monetary(string='Theoretical Cash (Total)', compute='_compute_expected_amounts')
    fixed_cash_amount = fields.Monetary(string='Fixed Cash Kept in POS', compute='_compute_expected_amounts')
    expected_transfer_amount = fields.Monetary(string='Expected Hand Over', compute='_compute_expected_amounts')
    transfer_amount = fields.Monetary(string='Amount to Hand Over', required=True, readonly=True)
    cash_received = fields.Monetary(string='Cash Received (If Different)')
    difference_amount = fields.Monetary(string='Difference', compute='_compute_difference_amount')

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        session_id = vals.get('session_id')
        if session_id:
            session = self.env['pos.session'].browse(session_id)
            if session.exists():
                fixed_cash_amount = max(session.cash_register_balance_start, 0.0)
                vals.setdefault('transfer_amount', max(session.cash_register_balance_end - fixed_cash_amount, 0.0))
        return vals

    @api.depends('session_id')
    def _compute_source_journal(self):
        for wizard in self:
            wizard.source_journal_id = wizard.session_id._get_clear_cash_source_journal()

    @api.depends('employee_public_id')
    def _compute_employee(self):
        for wizard in self:
            wizard.employee_id = wizard.employee_public_id.sudo().employee_id

    @api.depends('employee_public_id')
    def _compute_destination_journal(self):
        for wizard in self:
            employee = wizard.employee_public_id.sudo().employee_id
            wizard.destination_journal_id = employee.cash_journal_id

    @api.depends('session_id')
    def _compute_expected_amounts(self):
        for wizard in self:
            expected_amount = wizard.session_id.cash_register_balance_end
            fixed_cash_amount = max(wizard.session_id.cash_register_balance_start, 0.0)
            wizard.expected_amount = expected_amount
            wizard.fixed_cash_amount = fixed_cash_amount
            wizard.expected_transfer_amount = max(expected_amount - fixed_cash_amount, 0.0)
            wizard.transfer_amount = wizard.expected_transfer_amount

    @api.depends('expected_transfer_amount', 'transfer_amount', 'cash_received')
    def _compute_difference_amount(self):
        for wizard in self:
            actual_amount = wizard.cash_received if wizard.cash_received else wizard.transfer_amount
            wizard.difference_amount = wizard.expected_transfer_amount - actual_amount

    def _get_actual_transfer_amount(self):
        self.ensure_one()
        return self.cash_received if self.cash_received else self.transfer_amount

    def action_confirm(self):
        self.ensure_one()
        session = self.session_id
        currency = session.currency_id
        if session.state == 'handed_over':
            raise UserError(_("This session has already been handed over."))
        if session.state != 'closed':
            raise UserError(_("Clear Cash can only be confirmed on Closed & Posted sessions."))

        source_journal = self.source_journal_id
        destination_journal = self.destination_journal_id
        if not source_journal:
            raise UserError(_("No cash journal is configured for this Point of Sale."))
        if not destination_journal:
            raise UserError(_("The employee cash journal is missing."))
        if not source_journal.default_account_id or not destination_journal.default_account_id:
            raise UserError(_("Both source and destination journals must have a default account."))

        if not currency.is_zero(self.transfer_amount - self.expected_transfer_amount):
            raise UserError(_("The fixed POS cash amount cannot be moved."))

        actual_amount = self._get_actual_transfer_amount()
        if actual_amount < 0:
            raise UserError(_("Amount to hand over cannot be negative."))

        difference = self.expected_transfer_amount - actual_amount
        if not currency.is_zero(difference) and not self.cash_received:
            raise UserError(_("Please enter the cash received to confirm the difference."))
        company = session.company_id
        income_account = company.default_cash_difference_income_account_id
        expense_account = company.default_cash_difference_expense_account_id
        if difference > 0 and not currency.is_zero(difference) and not expense_account:
            raise UserError(_("Configure a Cash Difference Expense account on the company."))
        if difference < 0 and not currency.is_zero(difference) and not income_account:
            raise UserError(_("Configure a Cash Difference Income account on the company."))

        employee = self.employee_public_id.sudo().employee_id
        if not employee:
            raise UserError(_("The selected employee is not available."))

        lines = []
        if not currency.is_zero(actual_amount):
            lines.extend([
                (0, 0, {
                    'name': _('Cash handed over from %(source)s') % {'source': source_journal.display_name},
                    'account_id': source_journal.default_account_id.id,
                    'credit': actual_amount,
                    'debit': 0.0,
                }),
                (0, 0, {
                    'name': _('Cash received by %(employee)s') % {'employee': employee.name},
                    'account_id': destination_journal.default_account_id.id,
                    'debit': actual_amount,
                    'credit': 0.0,
                }),
            ])

        if difference > 0 and not currency.is_zero(difference):
            lines.append((0, 0, {
                'name': _('Cash shortage'),
                'account_id': expense_account.id,
                'debit': difference,
                'credit': 0.0,
            }))
            lines.append((0, 0, {
                'name': _('Cash shortage adjustment'),
                'account_id': source_journal.default_account_id.id,
                'credit': difference,
                'debit': 0.0,
            }))
        elif difference < 0 and not currency.is_zero(difference):
            overage = abs(difference)
            lines.append((0, 0, {
                'name': _('Cash overage'),
                'account_id': source_journal.default_account_id.id,
                'debit': overage,
                'credit': 0.0,
            }))
            lines.append((0, 0, {
                'name': _('Cash overage adjustment'),
                'account_id': income_account.id,
                'credit': overage,
                'debit': 0.0,
            }))

        move = False
        if lines:
            move = self.env['account.move'].sudo().create({
                'move_type': 'entry',
                'journal_id': destination_journal.id,
                'date': fields.Date.context_today(self),
                'ref': _('POS Cash Hand Over - %s') % session.name,
                'line_ids': lines,
            })
            move.sudo().action_post()

        session.sudo().write({
            'state': 'handed_over',
            'handed_over_by_id': self.env.user.id,
            'handed_over_at': fields.Datetime.now(),
            'handed_over_move_id': move.id if move else False,
            'handed_over_employee_id': employee.id,
        })
        session.sudo()._log_clear_cash_activity(actual_amount, self.expected_transfer_amount, difference, move, employee, self.cash_received)

        return {'type': 'ir.actions.act_window_close'}
