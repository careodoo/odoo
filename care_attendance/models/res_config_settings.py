from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bulk_attendance_approval = fields.Many2one('res.users',config_parameter='care_attendance.bulk_attendance_approval')

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        bulk_approver_group = self.env.ref(
            'care_attendance.group_bulk_attendance_approver', raise_if_not_found=False)
        if bulk_approver_group and self.bulk_attendance_approval and \
                self.bulk_attendance_approval.id not in bulk_approver_group.users.ids:
            # Add (not replace) so previously configured approvers are preserved.
            bulk_approver_group.users = [(4, self.bulk_attendance_approval.id)]
