import logging

from odoo import _, fields, models
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    _logger = logging.getLogger(__name__)

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        if len(self) == 1 and self.session_id.state == 'handed_over':
            timezone = self.env.tz
            vals['invoice_date'] = fields.Datetime.now().astimezone(timezone).date()
        return vals

    def _get_valid_session(self, order):
        PosSession = self.env['pos.session']
        closed_session = PosSession.browse(order['session_id'])

        self._logger.warning(
            'Session %s (ID: %s) was closed but received order %s (total: %s) belonging to it',
            closed_session.name,
            closed_session.id,
            order['uuid'],
            order['amount_total'],
        )

        open_session = PosSession.search([
            ('state', 'not in', ('closed', 'closing_control', 'handed_over')),
            ('config_id', '=', closed_session.config_id.id),
        ], limit=1)

        if open_session:
            self._logger.warning('Using open session %s for uuid number %s', open_session.name, order['uuid'])
            return open_session

        raise UserError(_('No open session available. Please open a new session to capture the order.'))

    def _process_order(self, order, existing_order):
        if order.get('session_id'):
            session = self.env['pos.session'].browse(order['session_id'])
            if session.state in ('closing_control', 'closed', 'handed_over'):
                order = dict(order)
                order['session_id'] = self._get_valid_session(order).id
        return super()._process_order(order, existing_order)
