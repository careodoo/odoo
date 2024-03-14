from odoo import fields, models, api
from odoo.exceptions import ValidationError


class PermissionRequestHour(models.Model):
    _name = 'permission.request.extra.hour'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Permission Request Hour'

    permission_request_id = fields.Many2one('permission.request')
    employee_id = fields.Many2one('hr.employee', required=True)
    hours = fields.Integer(required=True)
    date = fields.Date(required=True)
    approver_ids = fields.Many2many('res.users')
    state = fields.Selection(selection=[
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'), ('rejected', 'Rejected')
    ], default='draft')

    def button_submit(self):
        if self.hours <= 0:
            raise ValidationError("Please add hours!")
        self.state = 'submitted'
        for approver in self.approver_ids:
            self.sudo().activity_schedule(
                'permission_request.mail_act_permission_request_submit',
                summary='Permission Request for more Hours',
                note='Ask To Confirm Permission Request for more Hours',
                user_id=approver.id)

    def button_approve(self):
        self.state = 'approved'

    def button_reject(self):
        self.state = 'rejected'
