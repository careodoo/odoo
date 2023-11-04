from odoo import fields, models, api
from odoo.exceptions import ValidationError


class PermissionRequest(models.Model):
    _name = 'permission.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Permission Request'

    employee_id = fields.Many2one('hr.employee', required=True)
    employee_barcode = fields.Char(related='employee_id.barcode', store=True, string='Employee ID')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    position = fields.Char(related='employee_id.job_title', store=True)
    type = fields.Selection(selection=[
        ('official', 'Official'), ('personal', 'Personal')
    ], required=True)
    permission_from = fields.Datetime(required=True)
    permission_to = fields.Datetime(required=True)
    reason = fields.Text(required=True)

    @api.constrains('permission_from', 'permission_to')
    def check_dates(self):
        for rec in self:
            if rec.permission_from > rec.permission_to:
                raise ValidationError("From must be earlier than To!")
