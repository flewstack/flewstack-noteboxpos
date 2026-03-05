from odoo import api, models


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    @api.depends('config_ids')
    def _compute_open_session_ids(self):
        for payment_method in self:
            payment_method.open_session_ids = self.env['pos.session'].search([
                ('config_id', 'in', payment_method.config_ids.ids),
                ('state', 'not in', ['closed', 'handed_over']),
            ])
