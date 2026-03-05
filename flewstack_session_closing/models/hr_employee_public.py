from odoo import api, fields, models


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    cash_clear_id = fields.Char(compute="_compute_cash_clear_fields", readonly=True)
    cash_clear_password = fields.Char(compute="_compute_cash_clear_fields", readonly=True)
    cash_journal_id = fields.Many2one(
        "account.journal",
        compute="_compute_cash_clear_fields",
        readonly=True,
    )

    @api.depends("employee_id.cash_clear_id", "employee_id.cash_clear_password", "employee_id.cash_journal_id")
    def _compute_cash_clear_fields(self):
        can_read = self.env.user.has_group("hr.group_hr_user")
        for employee_public in self:
            if can_read:
                employee = employee_public.employee_id.sudo()
                employee_public.cash_clear_id = employee.cash_clear_id
                employee_public.cash_clear_password = employee.cash_clear_password
                employee_public.cash_journal_id = employee.cash_journal_id
            else:
                employee_public.cash_clear_id = False
                employee_public.cash_clear_password = False
                employee_public.cash_journal_id = False
