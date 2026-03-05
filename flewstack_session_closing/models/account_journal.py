from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    notify_user_id = fields.Many2one(
        'res.users',
        string='Notify User',
        help='User to notify when cash is transferred from this journal.'
    )
