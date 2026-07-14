from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class Employee(models.Model):
    _inherit = 'hr.employee'

    shift_request_records = fields.One2many('employee.shift.request.record', 'employee_id')
    open_shift_request_id = fields.Many2one('employee.shift.request', compute='_compute_open_shift',
                                            string='طلب نقل قائم')
    has_open_shift_request = fields.Boolean(compute='_compute_open_shift')

    def _compute_open_shift(self):
        closed = ['refuse_1', 'refuse_2', 'refuse_3', 'hr_refuse', 'done']
        Req = self.env['employee.shift.request']
        for emp in self:
            req = Req.search([('employee_id', '=', emp.id),
                              ('state', 'not in', closed)], limit=1)
            emp.open_shift_request_id = req.id
            emp.has_open_shift_request = bool(req)

    def action_open_shift_request(self):
        """Button on the employee file: transfer this worker to another
        project/department. Blocks if an open request already exists."""
        self.ensure_one()
        if self.has_open_shift_request:
            raise UserError(_(
                'يوجد طلب نقل قائم لهذا العامل (%s) لم يُعتمد بعد. لا يمكن إنشاء طلب جديد حتى يُغلق السابق.'
            ) % self.open_shift_request_id.display_name)
        if not self.department_id:
            raise UserError(_('العامل غير مرتبط بقسم/مشروع حالي.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('نقل العامل إلى مشروع/قسم آخر'),
            'res_model': 'employee.shift.request',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_employee_id': self.id,
                'default_current_department': self.department_id.id,
            },
        }

    def write(self, vals):
        res = super(Employee, self).write(vals)
        shift_request = self.env.context.get('shift_request', False)
        if vals.get('department_id'):
            if not self.env.user.has_group('hr_employee_shift.group_direct_shift_user') and not shift_request:
                raise ValidationError('You are not allowed to modify department directly, you should create shift request')
        return res


class EmployeeShiftRequestRecord(models.Model):
    _name = 'employee.shift.request.record'
    _description = 'Employee Shift Request History'

    employee_id = fields.Many2one('hr.employee')
    old_department = fields.Many2one('hr.department')
    new_department = fields.Many2one('hr.department')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent to Manager'),
        ('confirm', 'Confirmed'),
        ('approval_1', 'First Approved'), ('refuse_1', 'First Refused'),
        ('approval_2', 'Second Approved'), ('refuse_2', 'Second Refused'),
        ('approval_3', 'Third Approved'), ('refuse_3', 'Third Refused'),
        ('done', 'Shifted')], string='State')
    approver = fields.Many2one('res.users')
