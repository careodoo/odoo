from odoo import api, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _sync_dashboard_home_action(self):
        """The HR dashboard must NOT be forced as the login Home Action.
        It is reachable as the first page inside the Employees app instead.
        This only CLEARS a previously forced dashboard home action."""
        action = self.env.ref('care_hr.action_hr_dashboard', raise_if_not_found=False)
        if not action:
            return
        for user in self:
            if user.action_id.id == action.id:
                user.sudo().with_context(care_hr_sync=True).action_id = False

    @api.model
    def _clear_all_dashboard_home(self):
        """One-time cleanup: clear the forced dashboard home action for all users."""
        action = self.env.ref('care_hr.action_hr_dashboard', raise_if_not_found=False)
        if not action:
            return
        users = self.sudo().search([('action_id', '=', action.id)])
        users.with_context(care_hr_sync=True).write({'action_id': False})

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._sync_dashboard_home_action()
        return users

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('care_hr_sync'):
            keys = set(vals)
            if 'groups_id' in keys or any(
                    k.startswith(('in_group_', 'sel_groups_')) for k in keys):
                self._sync_dashboard_home_action()
        return res
