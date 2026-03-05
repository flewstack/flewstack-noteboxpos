from odoo import _, fields, models
from odoo.exceptions import UserError


class PosSessionClearCashAuth(models.TransientModel):
    _name = 'pos.session.clear.cash.auth'
    _description = 'POS Clear Cash Authentication'

    session_id = fields.Many2one('pos.session', required=True, readonly=True)
    clear_cash_id = fields.Char(string='Clear Cash ID', required=True)
    clear_cash_password = fields.Char(string='Password', required=True)

    def action_authenticate(self):
        self.ensure_one()
        session = self.session_id
        if session.state != 'closed':
            raise UserError(_("Clear Cash can only be performed on Closed & Posted sessions."))

        employee = self.env['hr.employee'].sudo().search([
            ('cash_clear_id', '=', self.clear_cash_id),
            ('cash_clear_password', '=', self.clear_cash_password),
        ], limit=1)
        if not employee:
            raise UserError(_("Invalid ID or password."))
        if not employee.cash_journal_id:
            raise UserError(_("The employee does not have a cash journal configured."))

        return {
            'name': _('Destination Journal'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.session.clear.cash.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_session_id': session.id,
                'default_employee_public_id': employee.id,
            },
        }
