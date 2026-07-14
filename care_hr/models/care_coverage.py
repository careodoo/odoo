# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import fields, models, api, _


class CareCoverageAlert(models.Model):
    """Attendance coverage alert: an active worker registered in the system
    but with no attendance/timesheet, or not assigned to a department.
    Populated by a daily scan; exempt workers (set from the worker file by
    the department manager) are skipped."""
    _name = 'care.coverage.alert'
    _description = 'Attendance Coverage Alert'
    _order = 'reason, employee_id'

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade')
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    job_id = fields.Many2one(related='employee_id.job_id', store=True)
    manpower_file_id = fields.Many2one(related='employee_id.manpower_file_id', store=True)
    reason = fields.Selection([
        ('no_dept', 'No Department/Job'),
        ('no_attendance', 'No Attendance'),
    ], required=True)
    last_attendance_date = fields.Date(string='Last Attendance')
    days_no_attendance = fields.Integer(string='Days No Attendance')
    scan_date = fields.Date(default=fields.Date.context_today)
    state = fields.Selection([
        ('open', 'Open'),
        ('resolved', 'Resolved'),
    ], default='open')

    @api.model
    def run_scan(self):
        """(Re)build the open coverage alerts. Returns the number of alerts."""
        Emp = self.env['hr.employee']
        Att = self.env['hr.attendance']
        ICP = self.env['ir.config_parameter'].sudo()
        today = fields.Date.today()
        days = int(ICP.get_param('care_hr.coverage_days') or 3)
        cutoff = today - timedelta(days=days)

        # auto-expire exemptions whose date passed
        Emp.search([('coverage_exempt', '=', True),
                    ('coverage_exempt_until', '!=', False),
                    ('coverage_exempt_until', '<', today)]).write({'coverage_exempt': False})

        emps = Emp.search([('active', '=', True), ('coverage_exempt', '=', False)])

        # employees WITH attendance in the window
        recent_grp = Att.read_group([('check_in', '>=', cutoff)], ['employee_id'], ['employee_id'])
        recent = {g['employee_id'][0] for g in recent_grp if g['employee_id']}
        # last attendance per employee (for reporting)
        last_grp = Att.read_group([], ['employee_id', 'check_in:max'], ['employee_id'])
        lastmap = {g['employee_id'][0]: g.get('check_in')
                   for g in last_grp if g['employee_id']}

        self.search([('state', '=', 'open')]).unlink()
        vals_list = []
        for e in emps:
            if not e.department_id or not e.job_id:
                vals_list.append({'employee_id': e.id, 'reason': 'no_dept'})
            elif e.id not in recent:
                last = lastmap.get(e.id)
                last_date = last.date() if last else False
                vals_list.append({
                    'employee_id': e.id, 'reason': 'no_attendance',
                    'last_attendance_date': last_date,
                    'days_no_attendance': (today - last_date).days if last_date else 999,
                })
        if vals_list:
            self.create(vals_list)
        return len(vals_list)

    def action_run_scan(self):
        n = self.run_scan()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Coverage Scan'),
                'message': _('%s coverage alert(s) found.') % n,
                'type': 'success', 'sticky': False,
                'next': {'type': 'ir.actions.act_window',
                         'res_model': 'care.coverage.alert',
                         'view_mode': 'tree,form',
                         'target': 'current',
                         'views': [(False, 'tree'), (False, 'form')]},
            },
        }

    def action_open_employee(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'res_model': 'hr.employee',
            'res_id': self.employee_id.id, 'view_mode': 'form',
        }
