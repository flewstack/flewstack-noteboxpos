from odoo import api, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.depends('session_ids', 'session_ids.state')
    def _compute_current_session(self):
        self.session_ids.fetch(["state"])
        for pos_config in self:
            opened_sessions = pos_config.session_ids.filtered(lambda s: s.state not in ('closed', 'handed_over'))
            rescue_sessions = opened_sessions.filtered('rescue')
            session = pos_config.session_ids.filtered(lambda s: s.state not in ('closed', 'handed_over') and not s.rescue)
            pos_config.has_active_session = bool(opened_sessions)
            pos_config.current_session_id = session and session[0].id or False
            pos_config.current_session_state = session and session[0].state or False
            pos_config.number_of_rescue_session = len(rescue_sessions)

    def _compute_statistics_for_session(self):
        for config in self:
            session = config.session_ids.filtered(lambda s: s.state not in ('closed', 'handed_over') and not s.rescue)
            session_record = session[0] if session else None
            if not session_record or not session_record.exists():
                config.statistics_for_current_session = False
                continue
            config.statistics_for_current_session = config.get_statistics_for_session(session_record)
