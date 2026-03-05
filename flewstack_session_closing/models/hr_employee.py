from odoo import fields, models


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    cash_clear_id = fields.Char(string='Clear Cash ID')
    cash_clear_password = fields.Char(string='Clear Cash Password')
    cash_journal_id = fields.Many2one(
        'account.journal',
        string='Employee Cash Journal',
        domain=[('type', '=', 'cash')],
        help='Cash journal used to receive handed over POS cash.'
    )
