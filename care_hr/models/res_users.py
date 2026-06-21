from odoo import api, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _sync_dashboard_home_action(self):
        """Members of group_hr_dashboard land on the HR dashboard on login
        (Home Action). Users removed from the group fall back to the normal
        app menu (action_id cleared, but only if it still points at our
        dashboard — we never touch a custom home action the user chose)."""
        group = self.env.ref('care_hr.group_hr_dashboard', raise_if_not_found=False)
        action = self.env.ref('care_hr.action_hr_dashboard', raise_if_not_found=False)
        if not group or not action:
            return
        for user in self:
            in_group = group in user.groups_id
            if in_group and user.action_id.id != action.id:
                user.sudo().with_context(care_hr_sync=True).action_id = action.id
            elif not in_group and user.action_id.id == action.id:
                user.sudo().with_context(care_hr_sync=True).action_id = False

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
