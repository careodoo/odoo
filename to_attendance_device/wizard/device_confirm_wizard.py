from odoo import models, fields


class DeviceConfirmWizard(models.TransientModel):
    _name = 'device.confirm.wizard'
    _description = 'Machine Confirm Wizard'

    def _default_attendance_device(self):
        return self.env.context.get('active_id')

    def _default_title(self):
        return self.env.context.get('title')

    def _default_content(self):
        return self.env.context.get('confirm')

    device_id = fields.Many2one('attendance.device', default=_default_attendance_device)
    title = fields.Char(string='Title of confirmation', default=_default_title)
    content = fields.Text(string='Confirmation content', default=_default_content)

    def ok(self):
        ctx_method = self.env.context.get('method', False)
        if ctx_method in (
            '_user_download',
            '_employee_map',
            '_finger_template_download',
            '_user_upload',
            '_attendance_clear',
            '_restart',
            '_icloud_download_users',
            '_icloud_download_fingers'
            ):

            getattr(self.device_id, ctx_method)()
