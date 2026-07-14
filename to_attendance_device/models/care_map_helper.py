# -*- coding: utf-8 -*-
from odoo import fields, models, api, tools


class CareAttendanceMonthly(models.Model):
    """Read-only SQL view: actual PRESENT DAYS (distinct punch-dates) per
    employee per month — what HR/payroll need, vs. raw punch counts."""
    _name = 'care.attendance.monthly'
    _description = 'Monthly Attendance Summary'
    _auto = False
    _order = 'period desc, present_days desc'

    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    department_id = fields.Many2one('hr.department', string='Department', readonly=True)
    period = fields.Date(string='Month', readonly=True)
    present_days = fields.Integer(string='Present Days', readonly=True)
    punches = fields.Integer(string='Punches', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW care_attendance_monthly AS (
                SELECT min(ua.id)                               AS id,
                       ua.employee_id                           AS employee_id,
                       e.department_id                          AS department_id,
                       date_trunc('month', ua.timestamp)::date  AS period,
                       count(DISTINCT ua.timestamp::date)       AS present_days,
                       count(*)                                 AS punches
                FROM user_attendance ua
                JOIN hr_employee e ON e.id = ua.employee_id
                WHERE ua.employee_id IS NOT NULL
                GROUP BY ua.employee_id, e.department_id,
                         date_trunc('month', ua.timestamp)
            )
        """)


class UserAttendance(models.Model):
    """Store the employee on each punch (related) so attendance can be
    pivoted/grouped by employee and month for the monthly summary."""
    _inherit = 'user.attendance'

    employee_id = fields.Many2one(
        'hr.employee', related='user_id.employee_id', store=True, index=True, string='Employee')


class AttendanceDeviceUser(models.Model):
    """Helper for the 'Map Workers' screen: show how many punches each device
    user has, so real workers (many punches) stand out from test/admin entries
    (0 punches) when mapping them to employees."""
    _inherit = 'attendance.device.user'

    att_punch_count = fields.Integer(string='Punches', compute='_compute_att_punch_count')

    def _compute_att_punch_count(self):
        UA = self.env['user.attendance']
        for r in self:
            r.att_punch_count = UA.search_count([('user_id', '=', r.id)]) if r.id else 0
