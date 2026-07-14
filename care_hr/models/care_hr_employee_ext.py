# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class HrEmployeeGrade(models.Model):
    """Link employees to a job grade / wage tier (foundation for payroll)."""
    _inherit = 'hr.employee'

    # --- Current worker status (shown in kanban + on the file) ---
    worker_status = fields.Selection([
        ('new', 'New / Mobilization'),
        ('active', 'Active (On Duty)'),
        ('on_leave', 'On Leave'),
        ('suspended', 'Suspended'),
        ('absconding', 'Absconding'),
        ('eos', 'End of Service'),
    ], string='Worker Status', default='active', tracking=True, index=True)

    # --- Attendance coverage exemption (dept-manager controlled) ---
    coverage_exempt = fields.Boolean(string='Exempt from Coverage Alerts', tracking=True)
    coverage_exempt_reason = fields.Char(string='Exemption Reason', tracking=True)
    coverage_exempt_until = fields.Date(string='Exempt Until', tracking=True)
    coverage_exempt_by = fields.Many2one('res.users', string='Exempted By', readonly=True)

    def write(self, vals):
        if vals.get('coverage_exempt'):
            for emp in self:
                is_mgr = (self.env.user.has_group('hr.group_hr_manager') or
                          self.env.user == emp.department_id.manager_id.user_id)
                if not is_mgr:
                    raise UserError(_(
                        'Only the department manager (or HR Manager) can exempt '
                        'a worker from coverage alerts, from the worker file.'))
            vals.setdefault('coverage_exempt_by', self.env.user.id)
        # keep the visible worker status in sync with suspension
        if 'suspend_date' in vals and 'worker_status' not in vals:
            vals['worker_status'] = 'suspended' if vals.get('suspend_date') else 'active'
        return super().write(vals)

    job_grade_id = fields.Many2one(
        'care.job.grade', string='Job Grade / Wage Tier', tracking=True)
    manpower_file_id = fields.Many2one(
        'care.manpower.file', string='Manpower File (PAM)', tracking=True,
        help='Government manpower file on which this worker is registered.')
    manpower_file_authority = fields.Selection(
        related='manpower_file_id.authority', string='File Authority', readonly=True)
    manpower_file_available = fields.Integer(
        related='manpower_file_id.available_count', string='File Quota Available', readonly=True)

    passport_ids = fields.One2many('care.passport', 'employee_id', string='Passports')
    passport_status = fields.Char(compute='_compute_passport_status', string='Passport Status')

    # --- biometric attendance punches (check-in/out) shown on the worker file ---
    device_attendance_ids = fields.Many2many(
        'user.attendance', compute='_compute_device_attendance',
        string='Attendance Records')
    device_attendance_count = fields.Integer(
        string='Attendance Punches', compute='_compute_device_attendance')
    present_days_month = fields.Integer(
        string='Present Days (This Month)', compute='_compute_present_days_month')

    def _compute_present_days_month(self):
        today = fields.Date.context_today(self)
        first = today.replace(day=1)
        for emp in self:
            if emp.id:
                self.env.cr.execute("""
                    SELECT count(DISTINCT ua.timestamp::date)
                    FROM user_attendance ua
                    WHERE ua.employee_id = %s AND ua.timestamp::date >= %s
                """, (emp.id, first))
                emp.present_days_month = self.env.cr.fetchone()[0] or 0
            else:
                emp.present_days_month = 0

    def _compute_device_attendance(self):
        ADU = self.env['attendance.device.user']
        UA = self.env['user.attendance']
        for emp in self:
            aus = ADU.with_context(active_test=False).search([('employee_id', '=', emp.id)]) if emp.id else ADU
            if aus:
                emp.device_attendance_count = UA.search_count([('user_id', 'in', aus.ids)])
                emp.device_attendance_ids = UA.search(
                    [('user_id', 'in', aus.ids)], order='timestamp desc', limit=300)
            else:
                emp.device_attendance_count = 0
                emp.device_attendance_ids = False

    def action_view_device_attendance(self):
        self.ensure_one()
        aus = self.env['attendance.device.user'].with_context(active_test=False).search(
            [('employee_id', '=', self.id)])
        return {
            'type': 'ir.actions.act_window',
            'name': _('Attendance Records — %s') % self.name,
            'res_model': 'user.attendance',
            'view_mode': 'tree,form',
            'domain': [('user_id', 'in', aus.ids)],
            'context': {'create': False},
        }

    def _compute_passport_status(self):
        for emp in self:
            pps = emp.passport_ids
            if not pps:
                emp.passport_status = 'No passport on file'
            else:
                out = pps.filtered(lambda p: p.state == 'out')
                if out:
                    emp.passport_status = 'Out (%s)' % ', '.join(
                        '%s · %s' % (p.out_reason or '', p.holder_id.name or '') for p in out)
                else:
                    emp.passport_status = 'In Archive'

    def action_open_manpower_file(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'care.manpower.file',
            'res_id': self.manpower_file_id.id,
            'view_mode': 'form',
        }
