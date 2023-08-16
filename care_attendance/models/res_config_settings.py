from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bulk_attendance_approval = fields.Many2one('res.users',config_parameter='care_attendance.bulk_attendance_approval')

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        bulk_approver_group = self.env['res.groups'].search([('full_name', '=', 'Bulk Attendance / Approver')])
        if self.bulk_attendance_approval.id not in bulk_approver_group.users.ids:
            bulk_approver_group.users = [(6, 0, self.bulk_attendance_approval.ids)]
